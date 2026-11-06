# Project proposal and implementation plan

**AI Security Agent** · Proposal dated November 4, 2026 · Updated November 6, 2026

Stages 0–3 are complete and verified. Stage 4 is implemented and undergoing integration verification. Stage 5, rules and baseline, follows acceptance. The [specification](specification.md) tracks the requirements and the [stage log](stage-log.md) records validation. Installation and user-facing operation are documented in the [README](../README.md).

## Project proposal

A site operator submits an authorized domain. Node.js collectors gather TLS, HTTP and DNS observations. The worker applies documented rules, correlates external evidence and presents each finding with its source, timestamp, severity and suggested repair. A Python model will evaluate candidates for repeat inspection. The experiment measures whether this reduces false positives while retaining real findings.

The demonstration begins with an expired lab certificate. The operator inspects the evidence, replaces the certificate and repeats the scan. The historical finding changes to resolved. A separate case uses mismatched endpoint evidence to demonstrate an actual false positive and its independent review.

The agreed scope is website and TLS configuration inspected by modules written in Node.js. The baseline accepts a hostname or extracts one from an HTTP(S) URL, checks the root route on approved ports 80 and 443, and supports manual scans of individual or bounded groups of targets. Scans use the operator's allowlist. Package auditing, static analysis, exploitation, crawling, automatic repair, scheduled scans, multi-tenant hosting, Kubernetes and an LLM chat interface fall outside this release. The proposal's reference to false positives is interpreted as reducing false alerts.

## Requirements and design choices

| Project requirement | Implementation and evidence |
| --- | --- |
| Node.js/Express, React and microservices | Independent API, worker, Python service and web UI. Verify with separate processes, containers and a browser workflow. |
| At least two external interfaces | A Google DNS adapter and an SSL Labs adapter. Use contract fixtures for deterministic tests and authorized live requests for integration acceptance. |
| Certificate and website assessment | Inspect validity, hostname, trust, key, signature, protocols, HTTP redirect and HSTS. Verify against known lab configurations. |
| AI/ML evaluation | Compare a reproducible baseline and two models on labeled findings. Publish metrics, provenance, error analysis and limits. |
| Load and durable results | Accept requests asynchronously, persist accepted jobs in MongoDB and run multiple BullMQ workers on Redis. Measure queue and HTTP behavior. |
| Delivery | Provide a specification, GitHub repository, YouTube video, poster and presentation. Verify each artifact before submission. |

The project brief also expects teamwork, attendance at weekly meetings, motivation, independent learning and individual responsibility. Engineering milestones are defined by deliverables and acceptance evidence, independently of team size or calendar availability.

## Target architecture and data flow

React submits a request to Express. The API verifies authorization, writes a durable MongoDB scan record, and dispatches the job through BullMQ on Redis. A stable job ID plus an outbox or reconciliation step recovers a request accepted just before a queue failure. The worker updates each source independently and writes observations and findings idempotently. A unique key includes scan, rule and endpoint. A separate correlation key supports rescans.

The worker owns TLS, HTTP and DNS collectors, the SSL Labs adapter and the deterministic rule engine. Each collector records an endpoint identity, source, timestamp and either evidence or an explicit collection error. The internal Python service accepts versioned features over HTTP and returns a decision, model identity and score when available. The worker owns persistence.

A scan follows queued → running → completed, partial or failed. The API returns HTTP 202 and a scan ID on acceptance. Treat timeout, DNS failure and unavailable providers as collection problems. Evaluate each rule as pass, fail, unknown or not_applicable. Preserve source, evidence, measurement time, remediation and severity on each finding. Store the ML assessment separately.

## Collection and provider policy

Validate all public-target DNS answers and pin connections to approved addresses. Preserve the logical hostname for SNI, SAN verification and HTTP Host. Limit redirects and revalidate every hop, including IPv4, IPv6 and IPv4-mapped IPv6. Keep the isolated lab allowlist separate. Use bounded timeouts, retries, response sizes and rate limits. Render untrusted fields as text. Keep private keys, environment values and sensitive raw scan data outside Git. [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) and [Node TLS](https://nodejs.org/api/tls.html).

Record validity windows against measurement time, compare SAN with the selected hostname, and verify the chain against an explicit trust profile. Keep verification errors from isolated invalid-certificate probes. A provider result or dedicated probe is needed for claims about supported protocols and cipher suites. Validate redirect destinations and read HSTS only over authenticated HTTPS. A closed port 80 is a different observation from an HTTP server returning a page without a redirect.

Google DNS supplies records for observation. Authorization comes from the server's target policy. SSL Labs provides corroborating TLS data for authorized public domains after registration. Disclose that the domain is sent to the provider, preserve original timestamps on cache hits, observe quotas, and poll an existing assessment. If access is unavailable, retain the open dependency or document and validate a replacement provider. [Google DNS JSON API](https://developers.google.com/speed/public-dns/docs/doh/json) and [SSL Labs v4](https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs-v4.md).

## Dataset and experiment

Start with about 50 labeled findings to assess review quality. The expansion target is 200–500 examples across at least 50 independent site or fixture groups. Include valid, expired, future, replaced and mismatched certificates, incomplete chains, approved private CAs, stale or partial evidence, redirects and HSTS. Mark simulated provider errors explicitly. Report class balance, provenance and limitations if false positives are sparse.

Compare logistic regression and a tree model such as random forest with the rules, deduplication and repeat-verification baseline. Candidate features include observation age, cross-source fingerprint agreement, repeated measurement consistency, rule type and chain completeness. Keep reviewer labels, later outcomes and post-decision information outside the feature set. Use known lab configuration or independent review to establish ground truth. Accepted risk and resolution are treatment states. Leave unresolved labels uncertain.

Group repeated sites, shared certificates and variants of a fixture family together. Use a documented train/validation/test split, initially 60/20/20 where feasible. Fit preprocessing on training data, tune the threshold on validation data and reserve the test set for final evaluation. Check calibration before displaying a probability. [Data leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) and [grouped splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html).

Report precision, recall, F1, confusion matrix, the count of true findings filtered and the change in false alerts. Break down performance by rule and source, with separate lab and authorized real-world results, sample counts and uncertainty. Target at least a 20% reduction in false alerts and at least 95% recall, with every verified critical finding visible. If evidence is insufficient, publish the result and keep the model in recommendation mode. Keep every scored finding accessible for review.

## Implementation stages

| Stage | Deliverable and acceptance evidence | Intended commit |
| --- | --- | --- |
| 0. Proposal | Define scope, architecture, ML experiment, external dependencies and acceptance criteria. Completed. | `docs: define project proposal and staged implementation plan` |
| 1. Bootstrap | Pin runtimes and lockfiles. Supply four processes, Compose, health checks, example configuration and CI. Verify the README, six-service stack and provider availability. Registration remains a stage 6 dependency. Completed. | `chore: bootstrap services docker and ci` |
| 2. Contracts and lab | Publish schemas, OpenAPI, rule severities, SNI, trust and address policy, labeling guide and disposable TLS servers. Every rule has pass/fail fixtures, collection failures are separate, and regenerated certificates use relative dates. Completed. | `test: add tls lab fixtures and scan contracts` |
| 3. Assets, scans, storage and queue | Add Asset and Scan APIs, allowlists, MongoDB indexes and BullMQ dispatch. Return 202 promptly. Prove persistence after restart and recovery after a worker or publish failure without duplicate results. Mark test jobs. Completed and verified with real-storage integration and Compose checks. | `feat: add asset scan persistence and job orchestration` |
| 4. TLS and HTTP collection | Store certificate, identity and HTTP evidence. Enforce network, timeout, size and redirect limits. Verify known lab identities, DNS rebinding, forbidden redirects and collection timeouts. Implemented, integration verification in progress. | `feat: collect tls and https evidence safely` |
| 5. Rules and baseline | Produce explained findings, handle inconclusive evidence, deduplicate and correlate rescans. Match the known lab outcomes, mark repaired findings resolved and account for stale measurements. | `feat: add explainable tls risk rules and baseline` |
| 6. External APIs | Add DNS and SSL Labs adapters, cache, polling, provider messages, bounded retries and partial results. Test READY, ERROR, partial, 429 and outages. Complete an authorized live smoke test for both providers. | `feat: integrate dns and external tls assessment` |
| 7. Dashboard and feedback | Add targets, progress, filters, evidence, history, JSON/CSV export and reasoned labels. Demonstrate scan → finding → feedback with loading, empty, error and partial states. Verify safe rendering of certificate text. | `feat: add scan dashboard evidence and feedback` |
| 8. Dataset | Review the pilot, deduplicate, freeze groups, splits and dataset version. Supply manifest, provenance, independent labels, class counts and a quality report. Document sampling limits. | `data: add labeled findings and reproducible dataset splits` |
| 9. Training and evaluation | Build the baseline and two training pipelines. Record seeds, versions, validation threshold, artifact manifest and model card. Reproduce held-out metrics and justify the deployment decision. | `feat: train and evaluate false positive models` |
| 10. ML integration | Add versioned inference, worker calls, abstention, prediction history and rollback. Expose model evidence and preserve rule results on service or schema failure. Route feedback through curated future dataset versions. | `feat: integrate versioned ml scoring with fallback` |
| 11. System and load tests | Exercise worker restarts, duplicates, timeouts and partial sources. Log scan IDs, measure queues, compare one and several workers. Verify 200 local jobs with 20 clients, p95 acceptance under 500 ms and zero lost jobs. Record hardware, full scan time and limits. | `test: verify end to end resilience and load targets` |
| 12. Submission | Verify installation in a clean checkout, prepare the demonstration, final specification, architecture, experiment, slide deck, poster and video. Open each file and verify the published YouTube and code links. | `docs: finalize specification demo and submission materials` |

## Delivery procedure and open decisions

Start each stage from the latest verified base. Read the specification, working agreement and stage log, implement the requested scope, run the relevant checks and update requirement status and history. Commit the stage on its branch, push normally and verify its remote checks before proceeding. Keep the repository README focused on running and using the available software. The stage log identifies each completed release.

| Dependency or risk | Decision |
| --- | --- |
| Ambiguous scope of Node.js modules | Proceed with site and TLS collection. Record a scope change if the instructor requires application source analysis. |
| Provider access or quota | Verify actual registration, authorization, rate limits and live evidence at stage 6. |
| Few independent false positives | Report sampling limits and use a clearly scoped lab experiment if necessary. |
| Model fails acceptance target | Deliver the experiment and leave filtering in recommendation mode. |
| High-load claims | Publish measured local results with hardware and distinguish dispatch latency from external-provider time. |
| Service complexity | Use one queue and three backend services. Review durable jobs against [BullMQ guidance](https://docs.bullmq.io/patterns/idempotent-jobs). |
| Video publication | Prepare the recording and description, then record the URL after an authorized upload. |
