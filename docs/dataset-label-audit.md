# E-PhishLLM label sample audit

Reviewed November 13, 2026 with AI assistance. Source revision and limitations are in the [dataset guide](dataset.md). No email was sent, no embedded link opened and no attachment executed. This document stores row references and judgments, not copied message text.

Sampling was fixed before inspection: for each publisher label, select the twelve `Language=en` rows with the smallest lexicographic SHA-256 of UTF-8 `label-audit-v1:<zero-based source row>`. The result is a small screening sample, not a statistically validated label-quality estimate. No labels were changed or rows removed based on these judgments. Students should independently review the cited rows locally before drawing model conclusions.

`Compatible` means the visible wording fits the source label. `Context-dependent` means missing sender identity, destination or attachment content prevents judging the source's phishing intent from this text alone. A compatible legitimate message can still conceal malicious context; a suspicious message is not independently proven phishing.

| Source row | Source label | Review | Evidence category |
| --- | --- | --- | --- |
| 3377 | legitimate | Compatible | Sustainability progress newsletter |
| 2251 | legitimate | Compatible | Organizational achievements and dates |
| 10186 | legitimate | Compatible | Conference speaking invitation |
| 6836 | legitimate | Compatible | Professional feedback request |
| 5892 | legitimate | Compatible | Packaging information request |
| 7007 | legitimate | Compatible | Sales progress feedback |
| 6476 | legitimate | Compatible | Internal brainstorming invitation |
| 6928 | legitimate | Compatible | Content-planning discussion |
| 7308 | legitimate | Compatible | Shipment scheduling confirmation |
| 268 | legitimate | Compatible | Product/pricing request with urgency; urgency alone is not phishing |
| 9291 | legitimate | Compatible | Team milestone update |
| 8887 | legitimate | Compatible | Market research summary |
| 5649 | phishing | Context-dependent | Urgent executive transfer request; no independent sender evidence |
| 15668 | phishing | Compatible | Download lure with an explicitly malicious synthetic placeholder |
| 15825 | phishing | Context-dependent | Large urgent payment request; recipient/account evidence absent |
| 4935 | phishing | Compatible | Credential verification under threat of account restriction |
| 16569 | phishing | Context-dependent | Design-feedback attachment request; attachment absent |
| 14458 | phishing | Context-dependent | Colleague login/help request; destination absent |
| 12947 | phishing | Context-dependent | Executive document-review request; attachment absent |
| 1762 | phishing | Compatible | Login verification under suspension threat |
| 14041 | phishing | Compatible | Urgent software-update link lure |
| 11672 | phishing | Compatible | Urgent software-installation request through a placeholder link |
| 11590 | phishing | Context-dependent | Newsletter article link; destination absent |
| 4073 | phishing | Context-dependent | Research collaboration attachment; attachment absent |

Result: 17 text-compatible and seven context-dependent examples. This is not a claim that 17 labels are verified correct or that seven are incorrect. The sample supports retaining explicit uncertainty about text-only observability. The corpus-wide placeholder count and required preprocessing decision are documented in the dataset guide.
