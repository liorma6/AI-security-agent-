# External audit label review

Reviewed November 13, 2026, before model scoring. Selection follows the frozen stage-4a protocol: eight messages per publisher class from the audit partition, ordered by the hash of their IDs. The reserve was not reviewed. This is an AI-assisted plausibility review for student verification, not an independent ground-truth adjudication. No labels or evaluation membership were changed following review.

Only extracted subject/body text was inspected. No message links were opened and no attachments or HTML were executed. IDs below refer to the locally prepared files; private message text, senders and addresses are not reproduced here.

| Example ID | Publisher label | Text-only observation |
| --- | --- | --- |
| external-easy-ham-2-000339 | Legitimate | Technical mailing-list reply about operating-system development; consistent with ham |
| external-easy-ham-2-000362 | Legitimate | Software-distribution discussion; consistent with ham |
| external-easy-ham-2-000391 | Legitimate | Quoted technical thread reply; consistent with ham |
| external-easy-ham-2-000515 | Legitimate | Request for service recommendations; consistent with ham |
| external-easy-ham-2-000744 | Legitimate | Forwarded news discussion; consistent with ham |
| external-easy-ham-2-001001 | Legitimate | Security discussion containing malicious-software terminology; those words alone do not make the email phishing |
| external-easy-ham-2-001155 | Legitimate | Software repository conversation with quoted text and signatures; consistent with ham |
| external-easy-ham-2-001300 | Legitimate | Discussion of advertising and spam with list footer; consistent with ham |
| external-nazario-2024-000030 | Phishing | Delivery lure, an apparently unrelated destination and extensive irrelevant padding; suspicious text cues |
| external-nazario-2024-000318 | Phishing | Invoice/voicemail attachment lure; authenticity depends on missing sender/attachment context |
| external-nazario-2024-000366 | Phishing | Plausible document-signing template; authenticity cannot be established from extracted text |
| external-nazario-2025-000109 | Phishing | Delayed-mail/purge pressure and visually substituted characters; suspicious text cues |
| external-nazario-2025-000240 | Phishing | HR-document lure and apparent displayed/destination mismatch in plain text; suspicious text cues |
| external-nazario-2025-000254 | Phishing | Password-expiry request asking for the same password; suspicious text cues |
| external-nazario-2025-000353 | Phishing | Security-alert imitation; sender and destination trust are needed to distinguish a genuine alert |
| external-nazario-2025-000389 | Phishing | The preferred plain MIME part is only an HTML-viewing placeholder; little task-relevant evidence reaches the classifier |

All eight ham selections are from `easy_ham_2`; the deterministic sample happens not to cover `hard_ham`. All eligible hard-ham messages still remain in the evaluation. Four phishing selections show suspicious textual cues, three need missing context, and one has an uninformative plain-text placeholder. These counts describe this small sample only. They do not estimate whole-corpus label accuracy or authorize relabeling based on model predictions.

The placeholder exposes a limitation of the predeclared plain-first MIME extraction. That rule was retained, and the message was not dropped. A future extraction change would be development work requiring a new protocol and evaluation; it must not be selected to improve this audit's score. Publisher labels remain the reference throughout. See the [source terms, protocol and limits](generalization-audit.md).
