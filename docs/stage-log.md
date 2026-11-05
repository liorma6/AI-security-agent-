# Stage and verification log

This log records the code, checks and dependencies for each stage. The [specification](specification.md) tracks requirements and acceptance criteria.

## Stage 0 — Proposal

Completed November 4, 2026. Selected authorized website and TLS assessment, documented the architecture and defined the stages and ML evaluation criteria. The proposal moved to the [implementation plan](implementation-plan.md) in stage 1. [Planning commit](https://github.com/liorma6/AI-security-agent-/commit/784f1adcff4a87df5e3027da5fdd3e5e9c2dd56d).

## Stage 1 — Service bootstrap

Completed November 4, 2026 on `stage/01-bootstrap`. Delivered the React interface, two Node.js services, Python service, locked environments, local launcher, Compose stack, browser checks and CI. Established the living specification and its update policy. [Implementation commit](https://github.com/liorma6/AI-security-agent-/commit/1d43bee47d045729698ce8471caec60ca2fa602d).

- Windows checks used Node.js 24.22.2, Python 3.13.16 and uv 0.13.1. ESLint, Ruff, four Node.js tests, two Python tests, the React build and the four-process smoke test passed. Both browser checks passed, including the unavailable-API case at mobile width. Desktop and mobile screenshots were inspected.
- Google DNS returned status 0 and SSL Labs info returned engine version 2.4.3. Assessment access and registration remain dependencies for stage 6.
- The production npm audit reported zero findings at the time. The development lint chain reported five moderate advisories involving minimatch. The lint tooling only consumes the repository configuration and is excluded from the final backend and web runtime images.
- The first CI run passed code and browser checks but failed MongoDB startup on the container runner kernel. Moving the container check to Ubuntu 22.04 resolved the compatibility issue. All six Compose services became healthy, and the service endpoints, static UI and same-origin proxy passed. Docker verification ran in CI. [Verified code](https://github.com/liorma6/AI-security-agent-/commit/9a82716e9d2fbd5c1ef98e60636483b1d7811a0b) and [stage 1 CI run](https://github.com/liorma6/AI-security-agent-/actions/runs/41848432558).

## Stage 2 — Contracts and TLS laboratory

Completed November 4, 2026 on `stage/02-contracts-and-lab`, based on stage 1 commit `bdacf0b`. Delivered shared contracts v1.0.0, the API description, ten rule definitions, the certificate generator, 18 loopback listeners, network and trust policies, and labeling guidance. FR14 and FR15 are implemented. Collection by the product, live provider assessment and ML training have separate acceptance gates. [Verified implementation](https://github.com/liorma6/AI-security-agent-/commit/92901314f13836613215946220dbb45b4779f1b6).

- The contract suites validated 17 accepted and 21 rejected examples in both languages. Review identified a missing optional Python date-time checker. The corrected environment installs format checkers and verifies rejection of an impossible date, malformed UUID and invalid IP. [jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/).
- The suite passed 50 Node.js tests, 41 Python tests and 12 lab subtests (13 test results including their parent). The lab covered SNI, trust profiles, certificate validity, chains, legacy protocols, redirect, HSTS and timeout. Tests inspected weak RSA and SHA-1 offline and marked provider failures as synthetic.
- ESLint, Ruff, OpenAPI lint, React build, four-process smoke and two browser tests passed. The production npm audit reported zero findings at the time.
- Both CI jobs passed. The Linux lab used OpenSSL 3.0.13 and the Windows lab used 3.2.4. Compose reported all six services healthy and passed all endpoint and web proxy checks. [stage 2 CI run](https://github.com/liorma6/AI-security-agent-/actions/runs/41897401889).

## November 5, 2026 — English documentation and interface

Published a practical README for the software in this branch, translated the specification and supporting records, and updated the page language, layout direction and browser assertions. The working agreement requires English for project files and visible interface text. The next functional stage is 3, assets, scans, storage and queue.

The English revision passed both the code/browser job and the six-service Docker Compose job. A repository-wide check covered 71 tracked files, internal documentation links and Markdown tables. [Verified commit](https://github.com/liorma6/AI-security-agent-/commit/c15981ad5e75f7270e1bdd268e345f92e380b5ec) and [CI run](https://github.com/liorma6/AI-security-agent-/actions/runs/41949219698).

For the next stage, record the date and branch, implemented requirements, actual checks, verified commit and CI run, open dependencies and next stage.
