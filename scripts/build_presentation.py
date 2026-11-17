"Build editable slides and an HTML/PDF companion from verified aggregate results."

import argparse
import base64
import html
import io
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree as ET
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=REPO / "outputs")
parser.add_argument("--template", type=Path, required=True)
parser.add_argument("--private-profile", type=Path)
args = parser.parse_args()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads((REPO / path).read_text(encoding="utf-8"))


r = read("docs/reports/final-evaluation.json")
verification = read("docs/reports/final-verification.json")
review = read("docs/reports/final-review.json")
assert verification["status"] == "verified"
labels = {
    "baseline_v2": "Baseline v2",
    "finetuned": "Original BERT",
    "defended": "Defended BERT",
    "pretrained": "HF DistilBERT",
}


def pct(x):
    return "N/A" if x is None else f"{100 * x:.2f}%"


clean = [["Model", "Accuracy", "Phishing recall", "Missed phishing", "False alarms"]]
for k, n in labels.items():
    m = r["clean"][k]["metrics"]
    c = m["confusion"]
    clean.append([n, pct(m["accuracy"]), pct(m["recall"]), str(c["fn"]), str(c["fp"])])
attack = [["Model", "Clean recall", "Attacked recall", "New misses / detected", "Candidate ASR"]]
for k in ["baseline_v2", "finetuned", "defended"]:
    m = r["robustness"]["models"][k]
    a = m["evasion"]
    attack.append(
        [
            labels[k],
            pct(m["clean"]["recall"]),
            pct(m["phishing_only_worst_of_budget"]["recall"]),
            f"{a['constraint_pass_successes']} / {a['eligible_clean_detected_phishing']}",
            pct(a["candidate_asr"]),
        ]
    )
shared = r["robustness"]["parent_defense_common_detected"]
parent = r["robustness"]["models"]["finetuned"]["evasion"]
defended = r["robustness"]["models"]["defended"]["evasion"]
slides = []


def add(title, subtitle="", bullets=None, table=None, note="", kind="text", image=None):
    slides.append(
        dict(
            title=title,
            subtitle=subtitle,
            bullets=bullets or [],
            table=table,
            note=note,
            kind=kind,
            image=image,
        )
    )


add(
    "PhishGuard",
    "Phishing detection and controlled adversarial robustness",
    [
        "Lior Mashaich & Sharon Elimelech",
        "Final project presentation | November 14, 2026",
        "An academic research prototype with a local email demo.",
    ],
    note=(
        "Introduce the research question and the two students. Development and do"
        "cumentation were AI-assisted; students must review and explain the imple"
        "mentation."
    ),
    kind="cover",
)
add(
    "What are we testing?",
    "Detection quality is only one part of the question.",
    [
        "Can a classifier separate phishing from legitimate email?",
        "Can small constrained text changes turn a detection into a miss?",
        "Does augmentation improve robustness without unacceptable clean-data cost?",
        "Can we demonstrate the result while making uncertainty visible?",
    ],
    note=(
        "Define a false negative as missed phishing and a false positive as a leg"
        "itimate message flagged incorrectly. A passing test suite does not prove"
        " detection quality."
    ),
)
add(
    "One pipeline, two separate workflows",
    "Offline experiments produce frozen artifacts; the UI only runs inference.",
    [
        "DATA: reviewed sources, inert extraction, deduplication and grouped splits.",
        "MODELS: classical baseline, pretrained comparison, fine-tuning and defense.",
        "EVALUATION: frozen clean inputs, bounded variants, metrics and verification.",
        "DEMO: paste text, select a model, inspect score, decision and evidence.",
    ],
    note=(
        "Explain why no training, email transmission or link following is availab"
        "le from the demo. Discuss the trust boundaries in the STRIDE chapter."
    ),
    kind="flow",
)
add(
    "Keep development separate from evidence",
    "Groups and derived variants stay together.",
    table=[
        ["Partition", "Messages", "Purpose"],
        ["Training", "3,261", "Fit the current local models"],
        ["Validation", "745", "Select checkpoints and thresholds"],
        ["Retrospective benchmarks", "423 + 2,000", "Historical and mainly synthetic challenge"],
        ["Final reserve", "703 / 432 groups", "Frozen evaluation after all choices"],
    ],
    note=(
        "The final reserve has 479 legitimate and 224 phishing messages. It was h"
        "eld out from local selection, but shares source families and years with "
        "development. It is not a new representative real-world inbox."
    ),
)
add(
    "Four preserved candidates",
    "Architecture and training history are different.",
    table=[
        ["Candidate", "How obtained", "Threshold", "Text budget"],
        ["Baseline v2", "TF-IDF + logistic regression", "0.31", "Full accepted text"],
        ["Original BERT", "Locally fine-tuned BERT-Tiny", "0.69", "256 tokens"],
        ["Defended BERT", "Separate augmentation continuation", "0.07", "256 tokens"],
        ["HF DistilBERT", "Existing pretrained phishing classifier", "0.45", "512 tokens"],
    ],
    note=(
        "The downloaded phishing classifier is distinct from the general BERT-Tin"
        "y encoder we fine-tuned. Thresholds were validation-selected, not tuned "
        "on the final reserve. Scores are not calibrated probabilities."
    ),
)
add(
    "The evaluation was frozen first",
    "Protocol and executable code committed before reserve scoring.",
    [
        ("Freeze commit: 77c4a17. It binds 96 source/reference files and 79 preserved inputs."),
        "All four models scored the same 703 clean messages with existing thresholds.",
        "The three trained candidates used the same seed-9042 attack bank.",
        "No refitting, relabeling, threshold changes or test-based model replacement.",
    ],
    note=(
        "Show the protocol commit and final report in GitHub. Explain the clean-w"
        "orktree gate, file hashes, development-overlap rejection and frozen post"
        "-score review selection."
    ),
)
add(
    "Final clean results",
    "703 held-out messages: 224 phishing and 479 legitimate.",
    table=clean,
    note=(
        "Read counts as well as accuracy. Compare the two error types explicitly."
        " These are source-conditioned held-out results; the same models behaved "
        "differently on the challenge dataset. Group-based intervals and per-sour"
        "ce results are in the report."
    ),
)
earlier = read("docs/reports/current-comparison.json")
table = [["Model", "Historical accuracy", "Challenge accuracy", "Final reserve accuracy"]]
for k, n in labels.items():
    table.append(
        [
            n,
            pct(earlier["cohorts"]["test"]["results"][k]["metrics"]["accuracy"]),
            pct(earlier["cohorts"]["challenge"]["results"][k]["metrics"]["accuracy"]),
            pct(r["clean"][k]["metrics"]["accuracy"]),
        ]
    )
add(
    "Changing the dataset changes the result",
    "Do not average different cohorts into one claimed product accuracy.",
    table=table,
    note=(
        "The historical cohort has 423 messages; the challenge has 2,000 and is m"
        "ainly generated; the reserve has 703 held-out messages. The pretrained c"
        "lassifier had 87.25% challenge accuracy but missed 136 of 1,000 phishing"
        " messages. Source and template effects matter."
    ),
)
add(
    "Controlled evasion, not unrestricted attacks",
    "A fixed, inspectable search budget.",
    [
        ("Three operations: duplicate a letter, swap internal letters, substitute a listed word."),
        "At most 3 changed words and 10% of body words; first 1,500 body characters only.",
        "Protect URLs, addresses, numbers, markup, capitalization and listed negations.",
        f"{r['bank']['variants']:,} candidates; "
        "at most 12 candidates plus 1 clean query per message/model.",
        "Automatic constraints do not certify that every candidate preserves meaning.",
    ],
    note=(
        "The generator never sees gradients or model scores. Each model scores th"
        "e same finite candidate bank. Original messages are included in minimum-"
        "score selection; legitimate originals stay clean in directed-evasion met"
        "rics."
    ),
)
add(
    "What happened under the fixed budget?",
    "Candidate ASR counts newly evaded, initially detected phishing.",
    table=attack,
    note=(
        "ASR is conditional: its denominator is initially detected phishing, incl"
        "uding examples without candidates. It is not the percentage of all mail."
        " Pretrained DistilBERT was not evaluated under attack. The three models "
        "each used "
    )
    + str(verification["queries_per_robustness_model"])
    + " total queries.",
)
add(
    "Did augmentation help?",
    "A separate preserved checkpoint, evaluated without retuning.",
    [
        f"Original / defended candidate ASR: {pct(parent['candidate_asr'])} / "
        f"{pct(defended['candidate_asr'])}.",
        f"Common clean-detected phishing: {shared['rows']}; "
        "newly evaded original / defended: "
        f"{shared['models']['finetuned']['constraint_pass_successes']} / "
        f"{shared['models']['defended']['constraint_pass_successes']}.",
        "Compare clean errors, fixed corruption and fresh search together.",
        ("Continued training and augmentation are combined; no clean-only continuation control."),
        "One seed and one finite search cannot establish universal robustness.",
    ],
    note=(
        "Use common eligibility to reduce the denominator mismatch. Explain the p"
        "aired whole-group clean contrast and ASR uncertainty. Do not attribute e"
        "very difference causally to augmentation."
    ),
)
add(
    "Review errors without changing the test",
    "A bounded, deterministic post-score review.",
    [
        f"Reviewed {review['clean_review_count']} unique clean cases "
        f"and {review['attack_review_count']} attack cases.",
        "Publisher labels remain fixed in primary metrics, even when context is incomplete.",
        "All 3 attack edits preserve meaning; the original phishing identity is ambiguous.",
        "No independently confirmed malicious-evasion lower bound above zero.",
        "AI-assisted inspection is not exhaustive independent human annotation.",
    ],
    note=(
        "The three reviewed defended successes are short sharing/account notifica"
        "tions. Their typos preserve meaning, but available text cannot independe"
        "ntly confirm a phishing identity. Thus 3/216 is publisher-label-dependen"
        "t candidate ASR. Keep labels unchanged and do not call these confirmed r"
        "eal-world malicious evasions. Raw text stays local. Explain nonidentifyi"
        "ng clean-error themes from the review report. Distinguish a model mistak"
        "e, missing evidence, and an uncertain publisher label. Students should i"
        "ndependently review the bounded sample."
    ),
)
add(
    "The local demonstration",
    "Choose a model, paste English email text, inspect the result.",
    [
        "127.0.0.1:7860 | local inference",
        "Score, decision, model identity and truncation",
        "Baseline term contributions; labeled text indicators",
        "No link fetching, message delivery or saved submissions",
        "Not flagged does not mean safe",
    ],
    note=(
        "Use invented public examples for the live demo. Show a normal result, a "
        "model change, the identity panel, an overlength error and Clear. Scores "
        "across models are not directly comparable."
    ),
    kind="demo",
    image=str(REPO / "assets/demo.png"),
)
add(
    "Verification is part of the deliverable",
    "Separate software correctness from model-quality evidence.",
    [
        "354 offline tests, including final-freeze and leakage guards.",
        "Two full final runs: identical prediction and candidate-bank bytes.",
        "Independent confusion / ASR / query recounts and unchanged 79 input files.",
        "Original neural tensors and all frozen thresholds remain unchanged.",
        "Windows + Linux CI; local demo and desktop/mobile browser checks.",
    ],
    note=(
        "A complete repeated run demonstrates numerical reproducibility in this e"
        "nvironment, not new independent statistical evidence. Reproduction instr"
        "uctions and all aggregate reports are versioned."
    ),
)
add(
    "What the project establishes",
    "A reproducible detection-and-robustness study with a working demo.",
    [
        "Model quality depends on source, wording, threshold and the chosen error cost.",
        "A small controlled edit can expose a miss; finite resistance is not a guarantee.",
        "The final reserve is now consumed and must not become a tuning set.",
        (
            "Next research: contemporary both-class data, independent labels, stronge"
            "r grouped evaluation, multiple seeds and a clean-only defense control."
        ),
    ],
    note=(
        "Conclude using the measured results, not a claim of a production email g"
        "ateway. Any future improvements need fresh held-out evidence. Discuss wh"
        "at an organization would still need before deployment."
    ),
)
add(
    "Reproduce, review, present",
    "Shared responsibility; transparent assistance.",
    [
        "Lior Mashaich: reproduction guide, local demonstration and packaging (W10: 5 units).",
        "Sharon Elimelech: comparative report, conclusions and presentation (W10: 5 units).",
        "Both students review the implementation and can explain the complete pipeline.",
        ("AI-assisted code and documents; assigned ownership is not invented personal authorship."),
        "Repository: github.com/liorma6/AI-security-agent- | docs/submission.md",
    ],
    note=(
        "Course submission and personal review remain human actions. Sources: sup"
        "plied Project2_PhishGuard brief; frozen dataset/model manifests; scikit-"
        "learn and Hugging Face documentation; TextAttack method reference; final"
        " protocol and measured reports."
    ),
)

profile = read("docs/project-profile.json")
slides[0]["bullets"] = [
    " & ".join(profile["students"]),
    "Supervisor: " + profile["supervisor"],
    profile["institution"] + " | " + profile["course"] + " | " + profile["updated"],
    "An academic research prototype with a local email demo.",
]

add(
    "Requirements: data and detectors",
    "PG01-PG05 | Specification requirements mapped to evidence.",
    table=[
        ["ID", "Requirement", "Evidence"],
        ["PG01", "Learn the foundations", "Learning record; personal evidence remains open"],
        ["PG02", "Collect and prepare data", "Pinned sources, grouped splits and manifests"],
        ["PG03", "Classical ML baseline", "TF-IDF + logistic regression; preserved v1/v2"],
        ["PG04", "Pretrained HF comparison", "Pinned DistilBERT; identical evaluation IDs"],
        ["PG05", "Fine-tune a transformer", "BERT-Tiny; validation selection and full repeat"],
    ],
    note="Map these rows to project-book section 3.18. Distinguish implemented artifacts "
    "from each student's remaining learning evidence. The external phishing classifier "
    "and the general encoder we fine-tuned are different models.",
)
add(
    "Requirements: evaluation and product",
    "PG06-PG10 | Explain both delivered behavior and its limits.",
    table=[
        ["ID", "Requirement", "Evidence"],
        ["PG06", "Controlled text evasion", "Three edit families, lineage and query caps"],
        ["PG07", "Measure degradation", "Clean/fixed/directed results and candidate ASR"],
        ["PG08", "Evaluate a defense", "Training-only augmentation; inconsistent gains"],
        ["PG09", "Pasted-email web demo", "Local UI, score, evidence and checked error states"],
        ["PG10", "Report and presentation", "Frozen final report, project book and this deck"],
    ],
    note="The defense requirement is implemented and measured. Do not present it as a "
    "guaranteed improvement. The One Pager, poster, source and links handoff support "
    "the additional submission checklist.",
)
add(
    "How the components communicate",
    "Separate inference, research workflows and frozen artifacts.",
    kind="figure",
    image=str(REPO / "assets/architecture-overview.png"),
    note="Use the component overview for an oral explanation. The detailed component and "
    "sequence UML are in chapter 7. The demo does not expose training or arbitrary "
    "model paths. The application uses versioned local files, not a user database.",
)
for item in slides:
    if item["title"] == "Changing the dataset changes the result":
        item["table"] = None
        item["kind"] = "figure"
        item["image"] = str(REPO / "assets/accuracy-by-cohort.png")
add(
    "Different errors have different costs",
    "Challenge cohort | 1,000 phishing and 1,000 legitimate messages.",
    kind="figure",
    image=str(REPO / "assets/challenge-error-tradeoff.png"),
    note="Read the two error counts separately. The pretrained classifier misses 136 "
    "phishing but produces 119 false alarms. The baseline misses 26 but produces "
    "372 false alarms. The challenge is mainly synthetic; this is not an inbox forecast.",
)
add(
    "The interface contract",
    "Documentation wireframe of implemented behavior, not an earlier design artifact.",
    kind="figure",
    image=str(REPO / "assets/ui-wireframe.png"),
    note="Walk through model selection, optional subject, body, Analyze and Clear. Explain "
    "the Ready, Analyzing, Result, Validation error and Model unavailable states. "
    "This is a schematic, while the following images are actual browser captures.",
)
add(
    "The same demo on mobile",
    "Actual stage-8 Chromium capture of the empty ready state.",
    bullets=[
        "The form and result stack vertically on a narrow screen.",
        "The same four model choices and validation rules apply.",
        "The result area is ready; no prediction is shown in this capture.",
        "Clear resets the displayed form and result.",
    ],
    kind="mobile",
    image=str(REPO / "assets/demo-mobile.png"),
    note="This is the recorded browser screenshot, not a generated mockup. Open the full "
    "resolution image or live UI to inspect small text. The form is empty and contains "
    "no email content. No new browser-verification run is claimed here.",
)
add(
    "Problems found and responses",
    "The research record includes unsuccessful results and boundary corrections.",
    bullets=[
        "Source shift: add external audits and report each cohort separately.",
        "Reviewed-family overlap: disclose it and exclude the whole family for later comparisons.",
        "Long emails: disclose token truncation instead of hiding discarded content.",
        "Small defense gains: retain clean-cost comparisons and state the missing control.",
    ],
    note="The two-row historical exclusion is documented, not erased. Better source-matched "
    "accuracy does not remove challenge weaknesses. A clean-only continued-training "
    "control and new independent labels remain future research.",
)
add(
    "Submission materials and demonstration",
    "A traceable handoff for review, reproduction and presentation.",
    bullets=[
        "One Pager, eight-chapter specification and English PowerPoint with notes.",
        "Measured reports, graphs, screenshots, interface wireframe and poster.",
        "GitHub source, source-only ZIP and local installation/demo instructions.",
        "Personal learning/review evidence and actual course submission remain open.",
    ],
    note="Repository: https://github.com/liorma6/AI-security-agent-. Use docs/submission.md "
    "and docs/submission-review.md. No recorded/published YouTube link exists in the "
    "verified package. Research datasets and learned weights are excluded from the code ZIP.",
)
add(
    "Table of Contents",
    "Course-template sequence",
    bullets=[
        "Software overview, goals, processes, modules and deliverables",
        "Specification requirements, algorithms and software",
        "Screenshots, measured graphs and interface mockup",
        "Progress against the plan, unexpected problems and responses",
        "Conclusions and directions for further development",
    ],
    note=(
        "The presentation follows the supplied course template. The final "
        "template slide contains design instructions and is not a project-"
        "content slide."
    ),
)
add(
    "General description of the software",
    "English email-text classification and controlled robustness research",
    bullets=[
        "Goals: compare detection, false alarms, controlled evasion and defense costs.",
        (
            "Processes: grouped preparation, training/selection, frozen evalua"
            "tion and local inference."
        ),
        "Modules: datasets, four classifiers, perturbations, verification and Gradio demo.",
        "Products: runnable code/demo, reports, project book, One Pager, poster and presentation.",
    ],
    note=(
        "PhishGuard is an academic local prototype. No mailbox ingestion, "
        "automatic blocking, attachment execution or production-email accu"
        "racy claim is provided."
    ),
)
add(
    "Project progress schedule",
    "Original milestone sequence compared with the actual project record",
    table=[
        ["Planned package", "Actual project outcome", "Comparison with plan"],
        [
            "W01-W03: foundations/data",
            "Contracts, manifests and grouped splits",
            "Implemented; individual review open",
        ],
        [
            "W04-W05: baseline/HF",
            "Baseline, HF comparison and audits 4a/4b",
            "External audit and refresh added",
        ],
        [
            "W06-W08: detector/robustness",
            "BERT-Tiny, evasion and defense measured",
            "Small, inconsistent defense gains",
        ],
        [
            "W09-W10: demo/final",
            "Demo checked; 703-message run repeated",
            "Materials ready; student review open",
        ],
    ],
    note=(
        "The original plan used relative packages, without dated baseline "
        "deadlines. A numerical early/late or on-time claim is unsupported"
        ". Actual implementation and experiment history is recorded in Nov"
        "ember 2026. The November-July student calendar was added afterwar"
        "ds; it is not the original implementation baseline. See docs/impl"
        "ementation-plan.md and docs/stage-log.md."
    ),
)
add(
    "Student learning and contribution schedule",
    "Confirmed November 2026-July 2027; 50 responsibility units per student",
    table=[
        ["Period", "Learning / responsibility", "Individual evidence"],
        [
            "November 2026",
            "W01-W02: foundations, contracts and threats",
            "Five foundation leads per student; code/test walkthrough",
        ],
        [
            "December-February",
            "W03-W05: data, baseline and pretrained comparison",
            "Ingestion/grouping, training/metrics and audit notes",
        ],
        [
            "March-May",
            "W06-W08: transformer, evasion and defense",
            "Training, bounded edits, ASR and defense review",
        ],
        [
            "June-July 2027",
            "W09-W10: demo, final interpretation and handoff",
            "Demo checks, personal reflection and presentation review",
        ],
    ],
    note=(
        "The calendar assigns personal study and review of existing AI-ass"
        "isted outputs. Eighteen log entries remain planned until actual d"
        "ates and evidence are supplied. It does not move completed experi"
        "ments into future months or create a new untouched reserve. "
        "Lior Mashaich and Sharon Elimelech each have 50 planning units, not lo"
        "gged hours."
    ),
)
add(
    "Unexpected problems",
    "Observed research and implementation difficulties",
    bullets=[
        "High internal accuracy did not transfer consistently to external cohorts.",
        "A reviewed example crossed a regrouping boundary in the refresh study.",
        "Long messages exceeded transformer token limits; some labels lacked context.",
        "Augmentation produced small, inconsistent robustness gains and clean costs.",
    ],
    note=(
        "These issues are documented in the external audit, refresh, fine-"
        "tuning, defense and final review. They are not erased by stronger"
        " source-matched final accuracy."
    ),
)
add(
    "Coping and Solving",
    "Responses, retained evidence and remaining limitations",
    bullets=[
        "Add external evaluation; report cohorts and error types separately.",
        "Disclose the boundary deviation; exclude the reviewed family in later comparisons.",
        "Show token truncation and review ambiguity without changing final labels.",
        "Preserve the original models; compare clean, fixed and fresh attack outcomes.",
    ],
    note=(
        "These responses improve traceability and interpretation; they do "
        "not prove domain-general detection or a universally effective def"
        "ense. Future causal claims need a clean-only continuation control"
        " and independent evidence."
    ),
)
add(
    "Conclusions for further development",
    "A reproducible prototype with clear research limits",
    bullets=[
        "Model preference depends on the cohort, missed phishing and false-alarm costs.",
        "Collect contemporary, independently reviewed data containing both classes.",
        "Evaluate multiple seeds and a clean-only continuation control for the defense.",
        "Use new held-out evidence before tuning; never recycle the consumed final reserve.",
    ],
    note=(
        "Final clean accuracy spans 95.16%-99.29%, while challenge accurac"
        "y spans 80.10%-87.25%. The local demo supports explanation and co"
        "mparison; it is not a deployed mailbox protection service. Studen"
        "ts must understand, review and present the AI-assisted implementa"
        "tion."
    ),
)
by_title = {item["title"]: item for item in slides}
order = [
    "PhishGuard",
    "Table of Contents",
    "General description of the software",
    "One pipeline, two separate workflows",
    "How the components communicate",
    "Requirements: data and detectors",
    "Requirements: evaluation and product",
    "Four preserved candidates",
    "Keep development separate from evidence",
    "The evaluation was frozen first",
    "Controlled evasion, not unrestricted attacks",
    "Did augmentation help?",
    "Verification is part of the deliverable",
    "The local demonstration",
    "The same demo on mobile",
    "Changing the dataset changes the result",
    "Different errors have different costs",
    "Final clean results",
    "What happened under the fixed budget?",
    "Review errors without changing the test",
    "The interface contract",
    "Project progress schedule",
    "Student learning and contribution schedule",
    "Unexpected problems",
    "Coping and Solving",
    "Submission materials and demonstration",
    "Conclusions for further development",
]
slides = [by_title[name] for name in order]
assert len(slides) == 27
for item in slides:
    if item["image"] and Path(item["image"]).name in [
        "accuracy-by-cohort.png",
        "challenge-error-tradeoff.png",
        "architecture-overview.png",
        "ui-wireframe.png",
    ]:
        image_path = Path(item["image"])
        item["image"] = str(image_path.with_name("course-" + image_path.name))
private = {}
if args.private_profile:
    private = json.loads(args.private_profile.read_text(encoding="utf-8"))
student_ids = private.get("student_ids", {})
cover_lines = [
    name + " | ID: " + student_ids.get(name, "pending") for name in profile["students"]
] + ["Supervisor: " + profile["supervisor"], "HIT | AB- Ai Security | November 17, 2026"]

prs = Presentation(args.template)
layout = prs.slides[2].slide_layout
hit_shape = next(
    shape for shape in prs.slides[0].shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
)
hit_blob = hit_shape.image.blob
hit_position = [hit_shape.left, hit_shape.top, hit_shape.width, hit_shape.height]
for sid in list(prs.slides._sldIdLst):
    prs.part.drop_rel(sid.rId)
    prs.slides._sldIdLst.remove(sid)
TEAL, TURQUOISE, INK, GOLD, WHITE = "23727B", "3CB3AA", "333E47", "EDA900", "FFFFFF"
html_slides = []
md = [
    "# PhishGuard - Final Project Presentation",
    "",
    (
        "Course-template content and speaker notes. Student identifiers ar"
        "e private local export fields and are not written here."
    ),
    "",
]


def textbox(slide, x, y, width, height, text, size=18, bold=False, align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.02)
    frame.margin_top = frame.margin_bottom = Inches(0.02)
    for i, line in enumerate(text.split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.text = line
        p.alignment = align
        p.font.name = "Calibri"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(INK)
        p.space_after = Pt(14 if size == 18 else 0)
        p.line_spacing = 1.1
    return shape


def image_html(path, alt):
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{data}">'


for i, s in enumerate(slides, 1):
    slide = prs.slides.add_slide(layout)
    for shape in list(slide.shapes):
        shape._element.getparent().remove(shape._element)
    slide.shapes.add_picture(io.BytesIO(hit_blob), *hit_position)
    textbox(slide, 11.4, 0.15, 1.65, 0.35, "PhishGuard", 16, True, PP_ALIGN.RIGHT)
    cover = s["kind"] == "cover"
    if cover:
        textbox(slide, 1.273, 3.717, 10.939, 0.774, s["title"], 36, False, PP_ALIGN.CENTER)
        textbox(slide, 1.273, 4.49, 10.939, 0.45, s["subtitle"], 18, False, PP_ALIGN.CENTER)
        textbox(slide, 1.273, 5.0, 10.939, 1.8, "\n".join(cover_lines), 18, False, PP_ALIGN.CENTER)
        content = (
            '<div class="cover-details">'
            + "".join("<p>" + html.escape(t) + "</p>" for t in cover_lines)
            + "</div>"
        )
    else:
        textbox(slide, 3.8, 0.576, 8.4, 1.313, s["title"], 36, False, PP_ALIGN.CENTER)
        textbox(slide, 1.273, 1.85, 10.8, 0.55, s["subtitle"], 18)
        if s["table"]:
            rows = s["table"]
            table = slide.shapes.add_table(
                len(rows), len(rows[0]), Inches(1.273), Inches(2.55), Inches(10.8), Inches(4.1)
            ).table
            widths = (
                [0.85, 3.15, 6.8]
                if s["title"].startswith("Requirements:")
                else {
                    3: [2.4, 4.2, 4.2],
                    4: [2.3, 5.0, 1.75, 1.75],
                    5: [2.25, 1.8, 2.0, 2.75, 2.0],
                }[len(rows[0])]
            )
            for column, width in zip(table.columns, widths, strict=True):
                column.width = Inches(width)
            for ri, row in enumerate(rows):
                for ci, value in enumerate(row):
                    cell = table.cell(ri, ci)
                    cell.text = value
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor.from_string(TEAL if ri == 0 else WHITE)
                    cell.margin_left = cell.margin_right = Inches(0.08)
                    cell.margin_top = cell.margin_bottom = Inches(0.06)
                    drawing_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
                    properties = cell._tc.get_or_add_tcPr()
                    for side in ["lnL", "lnR", "lnT", "lnB"]:
                        border_tag = "{" + drawing_ns + "}" + side
                        existing = properties.find(border_tag)
                        if existing is not None:
                            properties.remove(existing)
                        border = ET.SubElement(properties, border_tag, w="9525")
                        if side == "lnB":
                            fill = ET.SubElement(border, "{" + drawing_ns + "}solidFill")
                            ET.SubElement(fill, "{" + drawing_ns + "}srgbClr", val=TEAL)
                        else:
                            ET.SubElement(border, "{" + drawing_ns + "}noFill")
                    for p in cell.text_frame.paragraphs:
                        p.font.name = "Calibri"
                        p.font.size = Pt(18)
                        p.font.bold = ri == 0
                        p.font.color.rgb = RGBColor.from_string(WHITE if ri == 0 else INK)
                        p.line_spacing = Pt(20)
                        p.space_before = p.space_after = Pt(0)
            content = (
                "<table><colgroup>"
                + "".join(f'<col style="width:{w / 10.8 * 100:.3f}%">' for w in widths)
                + "</colgroup>"
                + "".join(
                    "<tr>"
                    + "".join(
                        f"<{'th' if ri == 0 else 'td'}>{html.escape(v)}"
                        f"</{'th' if ri == 0 else 'td'}>"
                        for v in row
                    )
                    + "</tr>"
                    for ri, row in enumerate(rows)
                )
                + "</table>"
            )
        elif s["kind"] == "figure":
            with Image.open(s["image"]) as picture:
                ratio = picture.width / picture.height
            width = min(10.8, 4.1 * ratio)
            slide.shapes.add_picture(
                s["image"], Inches((13.333333 - width) / 2), Inches(2.45), width=Inches(width)
            )
            content = '<div class="figure">' + image_html(s["image"], s["title"]) + "</div>"
        elif s["kind"] in ["demo", "mobile"]:
            mobile = s["kind"] == "mobile"
            slide.shapes.add_picture(
                s["image"], Inches(1.8 if mobile else 1.273), Inches(2.45), height=Inches(4.1)
            )
            textbox(
                slide,
                4.0 if mobile else 6.9,
                2.6,
                8.0 if mobile else 5.2,
                3.9,
                "\n".join("• " + b for b in s["bullets"]),
                18,
            )
            content = (
                '<div class="'
                + ("mobile" if mobile else "demo")
                + '">'
                + image_html(s["image"], s["title"])
                + "<ul>"
                + "".join("<li>" + html.escape(b) + "</li>" for b in s["bullets"])
                + "</ul></div>"
            )
        elif s["kind"] == "flow":
            for j, bullet in enumerate(s["bullets"]):
                x = 1.273 + j * 2.75
                box = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Inches(x), Inches(2.8), Inches(2.5), Inches(3.1)
                )
                box.fill.solid()
                box.fill.fore_color.rgb = RGBColor.from_string(WHITE)
                box.line.color.rgb = RGBColor.from_string(TURQUOISE)
                head, body = bullet.split(": ", 1)
                textbox(slide, x + 0.12, 3.0, 2.26, 0.6, head, 18, True)
                textbox(slide, x + 0.12, 3.7, 2.26, 2.0, body, 18)
            content = (
                '<div class="flow">'
                + "".join(
                    "<article><b>"
                    + html.escape(b.split(": ", 1)[0])
                    + "</b><p>"
                    + html.escape(b.split(": ", 1)[1])
                    + "</p></article>"
                    for b in s["bullets"]
                )
                + "</div>"
            )
        else:
            textbox(slide, 1.273, 2.6, 10.8, 4.0, "\n".join("• " + b for b in s["bullets"]), 18)
            content = (
                "<ul>" + "".join("<li>" + html.escape(b) + "</li>" for b in s["bullets"]) + "</ul>"
            )
    textbox(
        slide,
        1.273,
        7.05,
        10.2,
        0.25,
        "Lior Mashaich & Sharon Elimelech | HIT | AB- Ai Security",
        10,
    )
    textbox(slide, 11.6, 7.05, 0.5, 0.25, str(i), 10, align=PP_ALIGN.RIGHT)
    slide.notes_slide.notes_text_frame.text = s["note"]
    for shape in slide.shapes:
        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                paragraph.font.name = "Calibri"
    for paragraph in slide.notes_slide.notes_text_frame.paragraphs:
        paragraph.font.name = "Calibri"
    html_slides.append(
        '<section class="slide '
        + ("cover" if cover else "")
        + '"><img class="hit" alt="Supplied HIT artwork" src="data:image/png;base64,'
        + base64.b64encode(hit_blob).decode("ascii")
        + '"><div class="wordmark">PhishGuard</div><h1>'
        + html.escape(s["title"])
        + '</h1><p class="subtitle">'
        + html.escape(s["subtitle"])
        + '</p><div class="body">'
        + content
        + (
            "</div><footer><span>Lior Mashaich & Sharon Elimelech | HIT | AB- "
            "Ai Security</span><span>"
        )
        + str(i)
        + " / "
        + str(len(slides))
        + "</span></footer></section>"
    )
    md += [f"## {i}. {s['title']}", "", s["subtitle"], ""]
    if s["table"]:
        md += [
            "| " + " | ".join(s["table"][0]) + " |",
            "| " + " | ".join(["---"] * len(s["table"][0])) + " |",
        ]
        md += ["| " + " | ".join(row) + " |" for row in s["table"][1:]]
    else:
        md += ["- " + bullet for bullet in s["bullets"]]
    if cover:
        md += [
            "- Student IDs: omitted from public source; "
            "supplied through the private export profile."
        ]
    if s["image"]:
        md += ["", f"![{s['title']}](../{Path(s['image']).relative_to(REPO).as_posix()})"]
    md += ["", "Speaker notes: " + s["note"], ""]
prs.core_properties.title = "PhishGuard - Final Project Presentation"
prs.core_properties.author = "Lior Mashaich and Sharon Elimelech"
prs.core_properties.last_modified_by = "Lior Mashaich and Sharon Elimelech"
prs.core_properties.subject = "HIT; AB- Ai Security; Supervisor: Zimon Roi; course template"
target = OUT / "PhishGuard-Final-Presentation.pptx"
prs.save(target)
with ZipFile(target) as archive:
    parts = {name: archive.read(name) for name in archive.namelist()}
for name, data in list(parts.items()):
    if not name.endswith(".xml"):
        continue
    root = ET.fromstring(data)
    for element in root.iter():
        if element.text and re.search(r"[\u0590-\u05ff]", element.text):
            element.text = "Template placeholder"
        for key, value in list(element.attrib.items()):
            if re.search(r"[\u0590-\u05ff]", value):
                element.set(key, "Template element")
    parts[name] = ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for name, data in parts.items():
        archive.writestr(name, data)
style = """
@page{size:13.333333in 7.5in;margin:0}*{box-sizing:border-box}
body{margin:0;font-family:Calibri;color:#333e47;background:white}
.slide{position:relative;width:1280px;height:720px;page-break-after:always;overflow:hidden}
.slide:last-child{page-break-after:auto}.hit{position:absolute;left:0;top:0;width:338.1px;height:106.3px}
.wordmark{position:absolute;right:27px;top:14px;font-size:21.333px;font-weight:bold}
h1{position:absolute;left:364.8px;top:55.3px;width:806.4px;height:126px;font-size:48px;
font-weight:400;line-height:1.1;text-align:center;margin:0;padding:2px}
.subtitle{position:absolute;left:122.2px;top:177.6px;width:1036.8px;height:53px;font-size:24px;margin:0;line-height:1.1}
.body{position:absolute;left:122.2px;top:235.2px;width:1036.8px;height:398px}
ul{margin:0;padding-left:25px}li{font-size:24px;line-height:1.1;margin:0 0 19px}
table{width:100%;border-collapse:collapse;font-size:24px;table-layout:fixed}
td,th{padding:7px 8px;text-align:left;vertical-align:top;
border-bottom:1px solid #23727b;line-height:1.1}
th{background:#23727b;color:white}td,th{overflow-wrap:anywhere}
.figure{height:394px;width:100%;display:flex;justify-content:center}
.figure img{max-width:100%;height:394px;object-fit:contain}
.demo,.mobile{display:flex;gap:40px}.demo img{height:394px;width:auto}
.mobile{padding-left:50px;gap:100px}.mobile img{height:394px;width:auto}
.demo li,.mobile li{font-size:24px;line-height:1.1;margin-bottom:19px}
.flow{display:flex;gap:24px;padding-top:35px}
.flow article{width:240px;height:298px;border:1px solid #3cb3aa;
padding:20px 12px;font-size:24px}
.flow p{line-height:1.1;margin-top:30px}.flow b{font-size:24px}
footer{position:absolute;left:122px;right:116px;top:677px;font-size:13.333px;display:flex;justify-content:space-between}
.cover h1{left:122.2px;top:356.8px;width:1050.1px;height:74.3px}
.cover .subtitle{left:122.2px;top:431px;width:1050.1px;text-align:center}
.cover .body{top:480px;width:1050.1px;height:173px}.cover-details{text-align:center;font-size:24px}
.cover-details p{margin:0 0 19px;line-height:1.1}
"""
(OUT / "PhishGuard-Final-Presentation.html").write_text(
    (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Phish'
        "Guard final presentation</title><style>"
    )
    + style
    + "</style><body>"
    + "".join(html_slides)
    + "</body></html>",
    encoding="utf-8",
)
(REPO / "docs/presentation.md").write_text("\n".join(md), encoding="utf-8")
print(
    {
        "slides": len(slides),
        "template": "supplied course PPTX",
        "font": "Calibri",
        "title_pt": 36,
        "subtitle_pt": 18,
    }
)
