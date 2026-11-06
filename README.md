# AI Security Agent

AI Security Agent collects evidence about authorized websites' HTTPS and TLS configuration. Node.js workers inspect certificates, verify identity and trust, and record HTTP responses and redirects. MongoDB stores targets, scan state and observations. Redis and BullMQ dispatch work. A React page reports the API connection.

The current release provides collection through the API and command line. Scans finish **partial** while external DNS and SSL Labs evidence await stage 6. Risk findings, the full dashboard and ML scoring have later implementation stages.

## Install and start

Use Docker with Compose v2 and Linux containers. Clone the repository and copy .env.example to .env.

~~~sh
git clone https://github.com/liorma6/AI-security-agent-.git
cd AI-security-agent-
~~~

Set APP_MODE=collection and add the exact domains you are authorized to assess to ALLOWED_TARGETS in .env, separated by commas. The default allowlist is empty.

~~~sh
docker compose up --build --wait
docker compose ps
~~~

Open [the application](http://127.0.0.1:5173). Check dependencies at [API readiness](http://127.0.0.1:3001/ready) and [worker readiness](http://127.0.0.1:3002/ready). The current page shows the API connection. Submit scans with the API or command below.

Stop with docker compose down to retain stored data. Named volumes hold MongoDB and Redis data. The [runtime notes](docs/decisions/0001-runtime-and-local-environment.md) describe the verified MongoDB host kernel.

## Submit a scan and read evidence

With Node.js 24.22.2 installed, run this from the repository root, replacing the hostname with your allowlisted target.

~~~sh
npm run demo -- your-authorized-domain.example
~~~

The command creates the asset, submits a scan, prints its ID, polls the stored status and prints its observations. Collection begins only after a scan request. Allowlisted redirect destinations must also have permitted public DNS answers.

| Operation | Behavior |
| --- | --- |
| POST /api/assets | Normalize and store an authorized hostname or root URL. |
| GET /api/assets | List assets with a limit of 1–100 and cursor pagination. |
| POST /api/scans | Persist a request and return HTTP 202 with its Location. |
| GET /api/scans/{scanId} | Read status, execution mode, timestamps and source summaries. |
| GET /api/scans/{scanId}/observations | Read the bounded set of committed evidence and collection errors. |
| GET /health and /api/health | Read API liveness and capability flags. |
| GET /ready | Check MongoDB and Redis availability. |

Use the same Idempotency-Key header when retrying a scan request. Reusing a key for another asset returns 409. Accepted requests remain in MongoDB during a Redis outage. A storage failure returns 503. Execution mode is fixed when the request is accepted. Older orchestration requests retain their original behavior. [API contract](packages/contracts/openapi.json).

TLS observations contain certificate dates, SAN names, fingerprints, public key details, signature algorithm, chain and hostname verification, and the negotiated protocol/cipher. HTTP observations include endpoint identity, status, Location and authenticated HTTPS HSTS. Each observation records its measurement time and either evidence or a collection error. [Collection policy and limits](docs/decisions/0003-tls-http-collection.md).

## Local laboratory demonstration

Install the source dependencies below and OpenSSL 3.x. Place openssl on PATH or set OPENSSL_BIN to its executable.

~~~sh
npm run demo:lab
~~~

This command creates disposable certificates and loopback listeners, runs the product collector against an expired certificate and HTTP redirect, prints measured evidence, then removes the temporary lab. It runs independently of MongoDB and Redis.

For a queue-only demonstration, set APP_MODE=orchestration_test and ALLOWED_TARGETS=demo.example.com in .env, recreate the API and scanner containers, and run npm run demo -- demo.example.com. This mode exercises storage and dispatch and records unmeasured sources explicitly.

## Configuration

| Setting | Purpose |
| --- | --- |
| APP_MODE | collection enables TLS/HTTP collection. orchestration_test exercises the queue. Source defaults to bootstrap for UI development, while Compose defaults to collection. |
| ALLOWED_TARGETS | Exact comma-separated hostnames. Empty denies all targets. Restart API and worker after changes. |
| MONGO_URL / MONGO_DATABASE | Source defaults to mongodb://127.0.0.1:27017 and ai_security. |
| REDIS_URL / QUEUE_NAME | Source defaults to redis://127.0.0.1:6379 and scans. |
| WEB_PORT / API_PORT | Default host ports 5173 / 3001. |
| SCANNER_PORT / ML_PORT | Default host ports 3002 / 8000. |
| TLS_TRUST_PROFILES_FILE | Optional source-run JSON file binding an approved CA to an exact hostname. See the collection decision. |

Compose uses its internal mongo and redis service addresses. Application ports bind to loopback. Its development override exposes storage ports on loopback for source processes.

The supplied local MongoDB container has database authentication disabled and is reachable on the Compose service network. It uses a project-owned volume and requires no MongoDB Atlas account. Source processes use the official MongoDB Node.js driver and MONGO_URL. A shared or cloud deployment requires its own access and credential configuration.

## Run from source

Use Node.js 24.22.2, npm 11.19.1 and uv 0.13.1. uv installs the pinned Python 3.13.16 environment. After copying and configuring .env, start storage, install dependencies and launch the application.

~~~sh
docker compose -f compose.yaml -f compose.development.yaml up -d --wait mongo redis
npm ci
uv sync --project services/ml --frozen
npm run dev
~~~

Press Ctrl+C to stop application processes. Stop development storage using docker compose -f compose.yaml -f compose.development.yaml down. On Windows, use npm.cmd if PowerShell restricts npm.ps1.

## Checks and troubleshooting

Install source dependencies and OpenSSL before running the checks. Keep application ports free for smoke and browser tests.

~~~sh
npm run lint
npm test
npm run check:openapi
npm run test:lab
uv run --project services/ml --frozen ruff check --config services/ml/pyproject.toml services/ml tests/fixtures/tls
uv run --project services/ml --frozen pytest services/ml
npm run build
npm run smoke
npx playwright install chromium
npm run test:web
~~~

Run npm run test:integration with MongoDB and Redis reachable through MONGO_URL and REDIS_URL or their localhost defaults. Tests create isolated databases and queues, verify persistence and recovery, collect actual loopback TLS/HTTP evidence and remove their test data. CI provides real containers.

For a running Compose stack, use npm run smoke:stack. If a scan stays queued, inspect /ready and docker compose logs api scanner redis mongo. A 403 requires the exact hostname in ALLOWED_TARGETS. A target_blocked observation identifies a destination rejected during collection. After changing Compose configuration, run docker compose up -d --build.

## Documentation

- [System specification](docs/specification.md)
- [Architecture and recovery design](docs/architecture.md)
- [API and data contracts](packages/contracts/README.md)
- [TLS laboratory](tests/fixtures/tls/README.md)
- [TLS rules](docs/rules-and-policy.md)
- [Finding labeling guide](docs/labeling-guide.md)
