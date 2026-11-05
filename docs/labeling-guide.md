# Finding labeling guide

Version 1.0.0. A label answers whether a particular finding was correct for its endpoint, observation time and policy. Record the hostname, endpoint, certificate fingerprint, rule and policy version, SNI and trust profile. Match evidence from different sources to the same target and time window.

| Label | When to use it | Required evidence |
| --- | --- | --- |
| true_positive | The finding was correct at measurement time under the selected policy. | Independent evidence confirming the issue. |
| false_positive | The finding was wrong for that endpoint and time. | Counterevidence and an explanation of the error. |
| uncertain | Evidence is incomplete or conflicting. | An explanation of what is missing and what would resolve it. |

## Review procedure

1. Verify the hostname, endpoint identity, SNI, measurement time and trust profile.
2. Read the original observation and the rule that generated the finding.
3. Compare it with known lab configuration or an independent measurement with a recorded time.
4. Record the label, rationale, reviewer and observation references. Definitive labels require at least one evidence reference.
5. Preserve uncertain labels while reviewers resolve a disagreement.

Record treatment and truth separately. A certificate that expired and was replaced has a true_positive historical finding with treatment state resolved. A consciously accepted risk retains its truth label and receives the accepted_risk treatment state. Later measurements can reveal an intervening certificate replacement. A provider grade and a model score are supporting inputs and need independent review.

## Examples and data provenance

- **Expired fixture.** The validity window ends before generation time. A matching expiry finding is true_positive.
- **Private CA.** The operator authorized private-root.pem, but a measurement used root.pem. Verify which trust profile produced the finding. A failure assigned to the approved profile can be a false_positive.
- **Stalled handshake.** The timeout fixture supplies no certificate. Record an inconclusive collection result and keep a definitive TLS label pending evidence.
- **Certificate replaced since observation.** Retain the earlier true finding and record the repair against the subsequent observation.

Lab ground truth comes from server configuration, generated certificate properties, handshakes, identity and chain checks, and HTTP responses. DNS/provider failure examples are synthetic. Weak RSA keys and SHA-1 signatures are checked offline. The contract examples are test material. The feedback UI, labeled dataset and model experiment are scheduled for stages 7, 8 and 9 respectively.

Keep sites and related fixture families in one partition. Regenerating a certificate for the same scenario does not create an independent sample. Publish results separately for laboratory and real-site observations.
