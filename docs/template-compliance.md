# Course-template alignment

Updated November 17, 2026 against the supplied One Pager Template.docx and Presentation Template.pptx. These templates supersede the earlier example-based formatting choices. Working copies are kept locally outside Downloads; the original files are read-only inputs. Template Office files and private student identifiers are not committed to the public repository.

## One Pager

The Word export fills the actual template's thirteen native text boxes, retaining their positions, dimensions, borders, page size and institutional artwork. Both modern DrawingML and fallback text-box content are updated. Authored text uses Calibri. The PDF companion is exactly one A4 page and its text boxes were checked for overflow.

| Template field | PhishGuard content |
| --- | --- |
| Project name / organization / logo | PhishGuard; HIT; project text wordmark |
| Team details, IDs and project lead | Lior Mashaich and Sharon Elimelech; private ID fields; supervisor Zimon Roi; shared student coordination |
| Main points | Four-detector comparison, reproducibility and local demonstration |
| Problem / Solution | Changing phishing text and false alarms; comparative detection and bounded robustness study |
| The methodology | Grouped separation, validation-only selection, frozen final protocol and independent reproduction |
| System domain | English email-text research with local CPU inference |
| Modules / Interfaces | Data, classifiers, perturbations, evaluation; Gradio UI, CLI and setup downloads |
| Description of system components | Python, scikit-learn, PyTorch/Transformers, model registry and local files |
| Defining the goals of the project | Detection/error comparison, controlled evasion, defense costs and reproducible demonstration |
| Summary and Conclusions | Final/challenge accuracy ranges, cohort-dependent rankings and limited defense gains |

The original design-instruction footer is replaced by project/course and repository details. The supplied HIT artwork is retained as an institutional mark, including its original embedded lettering; all authored project prose remains English. The project wordmark is editable text, not an assertion that a separate graphic logo existed.

## Presentation

The export starts from the actual supplied PPTX, retaining its slide masters, white background, 16:9 canvas and HIT artwork placement. Template sample text is replaced by English project content; the final template slide is a design guide, not a project slide. The project wordmark appears at the upper right. All authored slide text uses Calibri, with 36-point titles and 18-point subtitles. Authored colors follow the supplied swatches: #3CB3AA, #23727B, #333E47 and #EDA900, with the template's white background. Charts and schematic diagrams have matching variants. Actual screenshots retain the implemented application's colors.

| Template topic | Completed slide coverage |
| --- | --- |
| Title, students, supervisor, IDs | Slide 1; full names and confirmed academic details, private IDs completed in local exports |
| Table of Contents | Slide 2 |
| General software description: goals/processes/modules/products | Slides 3-5 |
| Requirements from specification | Slides 6-7, PG01-PG10 with evidence |
| Algorithms and software | Slides 8-13, models, data, freeze, perturbations, defense and verification |
| Screenshots | Slides 14-15, actual desktop and mobile captures |
| Graphs | Slides 16-20, two measured charts, results and bounded review |
| Mockups | Slide 21, labeled wireframe of implemented behavior |
| Progress against the project schedule | Slide 22, original packages versus actual scope/outcomes; slide 23 separately shows the later November-July student calendar |
| Unexpected problems | Slide 24 |
| Coping and Solving | Slide 25 |
| Submission handoff | Slide 26 |
| Conclusions for further development | Slide 27 |

The original plan did not supply dated baseline deadlines. Slide 22 therefore compares planned scope and delivered outcomes without inventing schedule adherence. The November 2026-July 2027 student-learning calendar was added after implementation and is explicitly identified as such.

## Private fields and verification scope

Both templates request ID numbers. The student supplied both values on November 17, 2026. They are included in the local submission exports and excluded from the public repository. The builders accept an optional --private-profile JSON file containing a student_ids mapping keyed by full name. Keep it outside the repository. Only local Word/PowerPoint/HTML/PDF exports receive those values; public Markdown and logs do not.

Verified checks cover template-box geometry, retained branding, required sections, font settings, title/subtitle sizes, slide and PDF page counts, shape/page bounds, image loading and browser text overflow. Selected pages/slides were visually inspected. PDF companions render matching HTML in Chromium; this does not claim native Word/PowerPoint rendering. The template identity fields are completed in the local submission files; a public-source-only export without the private profile intentionally leaves the identifiers pending. Recorded video, personal contribution evidence and actual course submission remain separate open handoff items.

The export filenames are unchanged. PhishGuard-Links.txt is regenerated to point to the new committed sources and to name the corresponding local Word/PDF/PowerPoint files in the submission folder.
