"Build editable slides and an HTML/PDF companion from verified aggregate results."

import argparse
import base64
import html
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=REPO / "outputs")
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
        "Lior & Sharon Elimelech",
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
        "Lior: reproduction guide, local demonstration and packaging (W10: 5 units).",
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

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
TEAL = "12535B"
INK = "183B40"
MUTED = "4C686B"
CREAM = "F5F8F7"
WHITE = "FFFFFF"
GOLD = "D99B4E"


def box(slide, x, y, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(fill)
    shape.line.fill.background()
    return shape


def textbox(slide, x, y, w, h, text, size=22, color=INK, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Aptos"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
        p.space_after = Pt(13)
    return shape


html_slides = []
md = [
    "# PhishGuard final presentation",
    "",
    (
        "English slide content and speaker notes; generated artifacts are stored "
        "locally in the project outputs directory."
    ),
    "",
]
for i, s in enumerate(slides, 1):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    cover = s["kind"] == "cover"
    bg = TEAL if cover else CREAM
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(bg)
    box(slide, 0.55, 0.45, 0.12, 0.35, GOLD)
    textbox(
        slide,
        0.85,
        0.43,
        11.8,
        0.35,
        f"PHISHGUARD / {'FINAL PROJECT' if cover else 'RESEARCH & EVIDENCE'}",
        11,
        WHITE if cover else TEAL,
        True,
    )
    textbox(
        slide, 0.75, 1.02, 11.9, 0.9, s["title"], 38 if cover else 30, WHITE if cover else INK, True
    )
    textbox(slide, 0.77, 1.95, 11.8, 0.65, s["subtitle"], 20, "D4E7E4" if cover else MUTED)
    body_html = ""
    if s["table"]:
        rows = s["table"]
        width = 11.8
        height = min(3.8, 0.72 * len(rows))
        table = slide.shapes.add_table(
            len(rows), len(rows[0]), Inches(0.77), Inches(3.0), Inches(width), Inches(height)
        ).table
        for ri, row in enumerate(rows):
            for ci, text in enumerate(row):
                cell = table.cell(ri, ci)
                cell.text = text
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(
                    TEAL if ri == 0 else ("E5EFED" if ri % 2 else WHITE)
                )
                cell.margin_left = Inches(0.12)
                cell.margin_top = Inches(0.10)
                for p in cell.text_frame.paragraphs:
                    p.font.name = "Aptos"
                    p.font.size = Pt(15 if len(row) > 4 else 17)
                    p.font.color.rgb = RGBColor.from_string(WHITE if ri == 0 else INK)
                    p.font.bold = ri == 0
        body_html = (
            "<table>"
            + "".join(
                "<tr>"
                + "".join(
                    f"<{'th' if ri == 0 else 'td'}>{html.escape(t)}</{'th' if ri == 0 else 'td'}>"
                    for t in row
                )
                + "</tr>"
                for ri, row in enumerate(rows)
            )
            + "</table>"
        )
    elif s["kind"] == "demo":
        slide.shapes.add_picture(s["image"], Inches(0.77), Inches(2.8), height=Inches(3.95))
        textbox(slide, 6.35, 2.9, 6.1, 3.9, "\n".join("• " + x for x in s["bullets"]), 20)
        body_html = (
            '<div class="demo"><img src="'
            + "data:image/png;base64,"
            + base64.b64encode(Path(s["image"]).read_bytes()).decode("ascii")
            + '"><ul>'
            + "".join("<li>" + html.escape(x) + "</li>" for x in s["bullets"])
            + "</ul></div>"
        )
    elif s["kind"] == "flow":
        for j, t in enumerate(s["bullets"]):
            x = 0.77 + j * 3.0
            box(slide, x, 3.05, 2.8, 2.6, "E5EFED")
            head, body = t.split(": ", 1)
            textbox(slide, x + 0.17, 3.3, 2.45, 0.5, head, 20, TEAL, True)
            textbox(slide, x + 0.17, 3.95, 2.45, 1.55, body, 18)
        body_html = (
            '<div class="flow">'
            + "".join(
                "<article><b>"
                + html.escape(t.split(": ", 1)[0])
                + "</b><p>"
                + html.escape(t.split(": ", 1)[1])
                + "</p></article>"
                for t in s["bullets"]
            )
            + "</div>"
        )
    else:
        textbox(
            slide,
            0.8,
            2.95,
            11.6,
            3.8,
            "\n".join("• " + x for x in s["bullets"]),
            23 if len(s["bullets"]) < 5 else 21,
            WHITE if cover else INK,
        )
        body_html = (
            "<ul>" + "".join("<li>" + html.escape(x) + "</li>" for x in s["bullets"]) + "</ul>"
        )
    textbox(
        slide,
        0.8,
        7.0,
        11,
        0.22,
        "Frozen evaluation · English academic prototype · Lior & Sharon Elimelech",
        10,
        "D4E7E4" if cover else MUTED,
    )
    textbox(slide, 12.2, 7.0, 0.5, 0.23, str(i), 11, WHITE if cover else TEAL)
    slide.notes_slide.notes_text_frame.text = s["note"]
    html_slides.append(
        f'<section class="slide {"cover" if cover else ""}">'
        '<div class="eyebrow">PHISHGUARD / FINAL PROJECT</div>'
        f"<h1>{html.escape(s['title'])}</h1>"
        f'<p class="subtitle">{html.escape(s["subtitle"])}</p>'
        f'<div class="body">{body_html}</div>'
        "<footer><span>Frozen evaluation · Lior & Sharon Elimelech</span>"
        f"<span>{i} / {len(slides)}</span></footer></section>"
    )
    md += [f"## {i}. {s['title']}", "", s["subtitle"], ""]
    if s["table"]:
        md += (
            [
                "| " + " | ".join(s["table"][0]) + " |",
                "| " + " | ".join(["---"] * len(s["table"][0])) + " |",
            ]
            + ["| " + " | ".join(row) + " |" for row in s["table"][1:]]
            + [""]
        )
    else:
        md += ["- " + b for b in s["bullets"]] + [""]
    md += ["Speaker notes: " + s["note"], ""]
prs.core_properties.title = "PhishGuard - Final Project Presentation"
prs.core_properties.author = "Lior and Sharon Elimelech"
prs.core_properties.subject = "Frozen final evaluation; AI-assisted academic project"
prs.save(OUT / "PhishGuard-Final-Presentation.pptx")
style = (
    "@page{size:1280px 720px;margin:0}*{box-sizing:border-box}body{margin:0;f"
    "ont-family:Arial,sans-serif;color:#183b40;background:#f5f8f7}.slide{widt"
    "h:1280px;height:720px;padding:42px 70px;page-break-after:always;position"
    ":relative;overflow:hidden}.slide:last-child{page-break-after:auto}.eyebr"
    "ow{font-size:13px;font-weight:700;letter-spacing:2px;color:#12535b;borde"
    "r-left:8px solid #d99b4e;padding-left:18px}h1{font-size:39px;letter-spac"
    "ing:-1px;line-height:1.16;margin:36px 0 14px}.subtitle{font-size:23px;co"
    "lor:#4c686b;margin:0 0 32px}.body{height:420px;display:flex;align-items:"
    "flex-start;padding-top:12px}ul{margin:0;padding-left:24px;max-width:1100"
    "px}li{font-size:25px;line-height:1.5;margin-bottom:19px}table{border-col"
    "lapse:collapse;width:100%;margin-top:12px}td,th{padding:18px 14px;text-a"
    "lign:left;font-size:21px;line-height:1.25}th{background:#12535b;color:wh"
    "ite;font-size:19px}tr:nth-child(odd){background:#e5efed}footer{position:"
    "absolute;bottom:28px;left:70px;right:70px;display:flex;justify-content:s"
    "pace-between;color:#4c686b;font-size:13px}.cover{background:#12535b;colo"
    "r:white}.cover h1{font-size:65px;margin-top:58px}.cover .eyebrow,.cover "
    ".subtitle,.cover footer{color:#d4e7e4}.cover li{font-size:28px}.flow{dis"
    "play:flex;gap:20px;margin-top:32px}.flow article{width:270px;padding:26p"
    "x 22px;background:#e5efed;border-top:4px solid #12535b}.flow b{font-size"
    ":22px;color:#12535b}.flow p{font-size:22px;line-height:1.5}.demo{display"
    ":flex;gap:42px;width:100%}.demo img{height:405px;width:auto}.demo ul{pad"
    "ding-top:12px}.demo li{font-size:23px;margin-bottom:18px}"
)
(OUT / "PhishGuard-Final-Presentation.html").write_text(
    (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>PhishGuard f'
        "inal presentation</title><style>"
    )
    + style
    + "</style><body>"
    + "".join(html_slides)
    + "</body></html>",
    encoding="utf-8",
)
(REPO / "docs/presentation.md").write_text("\n".join(md), encoding="utf-8")
print({"slides": len(slides), "pptx": str(OUT / "PhishGuard-Final-Presentation.pptx")})
