# AI Security Agent — System Specification

Revision 0.3.0 · November 5, 2026 · Authorized assets, durable scan requests and queue processing

## Purpose and scope

The system is designed for a site operator who needs to assess an authorized website's HTTPS configuration, inspect the evidence behind a TLS finding and verify a repair. A later experiment will measure whether a model can reduce false alerts while retaining verified findings. This revision covers a single operator running the system locally.

The proposed Node.js modules collect evidence from websites. The assessment scope covers DNS, TLS certificates and the HTTP/HTTPS root on public ports 80 and 443. Package auditing, source-code analysis, crawling, exploitation and automatic repair are outside this scope. The original proposal uses “SSL” for certificate assessment. This specification uses “TLS” for the protocol the application will measure.

## Available in this revision

The React home page requests `GET /api/health` through its own origin and reports the connection state in English. Express and the scanner process each expose `GET /health`. FastAPI exposes its own `GET /health`. API and scanner processes configured for orchestration report `stage: 3` and `mode: "orchestration_test"`. Their /ready endpoints probe MongoDB and Redis. The bootstrap mode and ML service retain their own capability flags.

| Component | Observable behavior | Planned responsibility |
| --- | --- | --- |
| Web | Shows the result of a real API request on desktop and mobile | Manage assets, request scans, inspect evidence and give feedback |
| API | Normalizes and authorizes targets, persists scan requests, provides pagination and scan state | Serve evidence, findings and feedback |
| Scanner | Consumes jobs, rechecks authorization and commits an explicit partial orchestration result | Collect observations and evaluate rules |
| ML service | Reports `inference: false` and `modelLoaded: false` | Serve predictions for a versioned feature schema |
| MongoDB and Redis | Persist assets and scan state, enforce uniqueness and dispatch work | Support later observations and findings |

The development launcher runs the four application processes. Compose also runs MongoDB and Redis. The current UI can be exercised using the [installation and verification instructions](../README.md). Accepted scan requests persist across service restarts. The current worker labels its execution as an orchestration test and records each security source as unavailable. Site evidence and trained inference are scheduled for later stages.

## Operator workflows

| ID | Workflow | Stage |
| --- | --- | --- |
| UC01 | Open the home page and check whether the web interface can reach the API. | 1, available |
| UC02 | Add an authorized domain and submit a scan. | 3 and 7 |
| UC03 | Follow scan progress and distinguish complete from partial results. | 3–7 |
| UC04 | Read the finding, its severity, evidence and recommended fix. | 5 and 7 |
| UC05 | Label a finding and record the supporting evidence. | 7 |
| UC06 | Compare a repeat scan after correcting an issue. | 5 and 7 |
| UC07 | Inspect the model recommendation and the limits of its evidence. | 9 and 10 |
| UC08 | Export results and prepare a reproducible demonstration. | 7 and 12 |

## Functional requirements

| ID | Acceptance criterion | Status |
| --- | --- | --- |
| FR01 | Start the four application components, load React and read each backend's health response. | Verified in stage 1 |
| FR02 | When the API is unreachable, show a visible failure state on desktop or mobile. | Verified in stage 1 |
| FR03 | Normalize a submitted hostname and authorize it against server policy. | Implemented in stage 3, integration verification in progress |
| FR04 | Return HTTP 202 with a scan ID, persist the request and recover from duplicate jobs or a failed dispatch. | Implemented in stage 3, integration verification in progress |
| FR05 | Collect TLS and HTTP observations that match known lab configurations. | Planned, stage 4 |
| FR06 | Return pass, fail, unknown or not_applicable with evidence, policy version and severity where applicable. | Planned, stage 5 |
| FR07 | Integrate Google Public DNS and SSL Labs and verify each with an authorized live target. | Availability probed in stage 1. Integration planned for stage 6 |
| FR08 | Show severity, source, measurement time, evidence and remediation for each finding. | Planned, stage 7 |
| FR09 | Export results and record reasoned labels independently of treatment state. | Planned, stage 7 |
| FR10 | Record provenance, label rationale and group membership for training data. | Planned, stage 8 |
| FR11 | Reproduce training and compare against a fixed baseline on held-out groups. | Planned, stage 9 |
| FR12 | Continue to display rule findings when the model abstains or fails. | Planned, stage 10 |
| FR13 | Deliver the specification, repository, YouTube video, poster and presentation. | Final delivery planned for stage 12 |
| FR14 | Validate the same wire-format examples in JavaScript and Python and lint the OpenAPI description. | Verified in stage 2 |
| FR15 | Provide passing and failing fixtures for every rule, regenerate certificates relative to the current clock and distinguish collection errors. | Verified in stage 2 |

## Quality requirements

| ID | Requirement and verification |
| --- | --- |
| NFR01 | Reproduce installations with pinned runtimes, dependency lockfiles and versioned images. Review image digests for final delivery. |
| NFR02 | Run the web, API, scanner and ML components as separate processes and containers. |
| NFR03 | Measure acceptance latency for 200 local jobs with 20 concurrent clients. The stage 11 target is p95 below 500 ms with zero lost jobs. Report full scan time separately. |
| NFR04 | Use durable requests, idempotent writes and queue reconciliation. Verify recovery by interrupting dispatch and restarting a worker. |
| NFR05 | Keep collection failures distinct from confirmed weaknesses. Identify partial scans, cached observations and simulated providers. |
| NFR06 | Publish application ports on loopback and keep storage and queue ports internal to Compose. |
| NFR07 | Exclude credentials, private scan data, generated keys, environment files and private model artifacts from Git. |
| NFR08 | Update the specification and record the tested commit, evidence and open dependencies for each stage. |
| NFR09 | Provide an English, left-to-right interface with readable mobile layouts and explicit connection errors. |

## Data and interface design

The [JSON Schema and OpenAPI description](../packages/contracts/README.md) define version 1.1.0 and continue to validate version 1.0.0 records. The update adds an execution-mode label, operational health and readiness, and unavailable-storage errors. OpenAPI identifies implemented asset and scan operations. JavaScript and Python validate the same 17 accepted and 21 rejected examples. Both check dates, UUIDs and IP addresses. The target data model separates measurements, rule decisions and human review.

| Record | Meaning |
| --- | --- |
| Asset | Normalized hostname with authorization granted by server policy. |
| Scan | Asset, attempt, policy version, timestamps and the status of each source. A scan moves from queued to running, then completed, partial or failed. |
| Observation | Source, measurement and retrieval time, hostname, endpoint and source-specific evidence. A collection error carries an error reason. |
| RuleResult and Finding | A failed rule can produce a finding with observation references, severity and remediation. Insufficient evidence yields unknown. |
| Feedback | A reviewer supplies a label, rationale and evidence references. Treatment states include resolved and accepted_risk. |
| ModelVersion and prediction | Record the feature and dataset versions, artifact identity, evaluation scope and threshold. A prediction carries a score or an explicit abstention. |

The API accepts targets at `/api/assets` and jobs at `/api/scans` in orchestration mode. A scan request returns HTTP 202 and a location to poll. Findings, feedback, state changes and exports have separate operations. The worker will call the internal `POST /predict` endpoint. The service checks exact-hostname authorization, asset references and request-key consistency. Unique indexes arbitrate asset creation and idempotent scan requests. POST /api/scans returns after a journaled MongoDB write. A dispatcher retries incomplete requests using the scan UUID as the queue job ID. The worker records attempts, rechecks policy and conditionally commits one terminal result. [Recovery decision](decisions/0002-durable-orchestration.md).

## Collection policy and laboratory

The API and worker enforce the same exact-hostname allowlist. Input is normalized for case, trailing dots and IDNA. IP literals, credentials, unsupported ports and non-root URLs are rejected. Network-level checks belong to the collector stage. Validate every A and AAAA answer, handle IPv4-mapped IPv6 addresses and reject non-public destinations. Connect to the validated address using the original hostname for Host, SNI and identity verification. Reapply the policy to each redirect. Bound response size, timeouts, retries, redirects and per-domain concurrency. Render certificate and HTTP values as text.

Record certificate validity against the observation time, hostname against SAN, the selected trust profile, certificate chain, key and signature information. A dedicated probe may inspect an invalid certificate and retain its verification error. External provider connections use ordinary TLS verification. An approved private CA belongs to the target's trust profile.

The [rule policy](rules-and-policy.md) covers expiry, future validity, approaching expiry, hostname, trust chain, key strength, signature, legacy protocols, HTTP redirect and HSTS. An expiry warning applies within 30 days of a currently valid certificate's expiry. A single negotiated protocol provides evidence only for that connection.

The lab generates fresh certificates and starts 18 ephemeral loopback listeners. It verifies SNI selection, complete and incomplete chains, trust profiles, handshakes, redirects, HSTS and timeouts. Weak RSA and SHA-1 fixtures are inspected offline. DNS and provider failure examples are explicitly synthetic. Each rule has a positive and a negative fixture. The product collector and rule engine are scheduled for stages 4 and 5. [Laboratory guide](../tests/fixtures/tls/README.md).

## Data science and evaluation

Use evidence from the same endpoint, time, certificate and trust profile to label a finding true_positive, false_positive or uncertain. A certificate that actually expired and was later replaced is a true finding with a resolved treatment state. The [labeling guide](labeling-guide.md) defines the review procedure. A model will rank candidates for repeat inspection while factual TLS findings retain their rule severity.

Compare logistic regression and a tree model with a rules, deduplication and repeat-verification baseline. Group samples by site, shared certificate or fixture family. Fit preprocessing on the training partition and choose the threshold on validation data before opening the held-out test partition. Report precision, recall, F1, a confusion matrix, uncertainty, class counts and errors by source and rule.

The experimental target is at least 20% fewer false alerts at 95% or higher recall, with every verified critical finding still visible. A small or inconclusive sample supports recommendation-only operation. Data collection, model training and measured performance are future work.

## Integration dependencies and delivery

On November 4, 2026, the availability probe obtained Google DNS status 0 for example.com and SSL Labs engine version 2.4.3 from the v4 info endpoint. Live SSL Labs assessment still requires registration and an authorized target. Keep provider measurement time and cache age, honor rate limits and mark incomplete scans as partial.

Delivery includes this specification, a GitHub repository, a reproducible ML experiment, an installation guide, a demonstration video with a published YouTube link, a poster and a presentation. Final verification includes opening every artifact and reproducing the demo from a clean checkout.

## Revision and validation history

| Date | Scope | Evidence |
| --- | --- | --- |
| November 4, 2026 | Stage 0 defined scope, proposal and implementation plan. | [Planning commit](https://github.com/liorma6/AI-security-agent-/commit/784f1adcff4a87df5e3027da5fdd3e5e9c2dd56d) |
| November 4, 2026 | Stage 1 delivered four application components, health endpoints, Compose, build, smoke and browser checks. | Four Node.js tests, two Python tests, two browser tests and a six-service Compose run. [Stage 1 results](https://github.com/liorma6/AI-security-agent-/actions/runs/41848432558) |
| November 4, 2026 | Stage 2 delivered contracts, policy, labeling guidance and the certificate laboratory. | 50 Node.js tests, 41 Python tests, 12 lab subtests, two browser tests and both CI jobs passed. [Stage 2 results](https://github.com/liorma6/AI-security-agent-/actions/runs/41897401889) |
| November 5, 2026 | Stage 3 adds assets, persistent requests, queue dispatch, readiness and recovery tests. | Local input, contract, build and browser checks passed. Real-storage CI verification is in progress. |
| November 5, 2026 | Adopted English for project material and the UI. Published operating instructions and updated the specification. | The browser suite checks English content, page direction and API connection states. |

See the [stage log](stage-log.md) for validation details and open dependencies, the [architecture](architecture.md) for runtime boundaries and the [implementation plan](implementation-plan.md) for upcoming work.
