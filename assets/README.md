# Presentation assets

`demo.png` is a local PhishGuard screenshot using an invented routine meeting message. It contains no research email, credentials or private user input. The presentation builder embeds this image in its editable PPTX and self-contained HTML output.

`phishguard-poster.png` is the AI-assisted illustrated academic poster prepared from the student's design reference, with PhishGuard content and both students' full names. Its numerical table matches the frozen final evaluation. The laptop and small decorative chart are illustrations. See [poster documentation](../docs/poster.md) for source data and local export details.

`demo-mobile.png` is the actual stage-8 Chromium capture of the empty ready state at a 390-pixel viewport. It contains no submitted email. Desktop and mobile screenshots accompany the recorded [browser checks](../docs/reports/demo-browser-checks.json); adding them to the book does not claim a new browser test.

`accuracy-by-cohort.png` / `.svg` and `challenge-error-tradeoff.png` / `.svg` are measured plots generated from committed aggregate reports by [the visual builder](../scripts/build_submission_visuals.py). Accuracy axes start at zero. Cohorts are different populations, not a time trend; the challenge is mainly synthetic.

`architecture-overview.svg` / `.png` summarizes implemented component responsibilities. `ui-wireframe.svg` / `.png` is an explanatory wireframe of the implemented screen, prepared during submission documentation. It is distinct from an actual screenshot and is not represented as a historical design artifact. SVG files remain editable; PNG equivalents support Word and PowerPoint embedding.

The course-prefixed chart and diagram variants use the supplied presentation palette and Calibri for the course-template deck. Their data and architectural meaning are unchanged. The chart builder's --course-template option requires Calibri to be installed and writes these variants separately, preserving the original book figures. Screenshots are retained unchanged as evidence of the implemented application.
