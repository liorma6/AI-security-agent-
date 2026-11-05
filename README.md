# AI Security Agent

AI Security Agent is a local toolkit for building evidence-based HTTPS and TLS assessments. The current version stores authorized targets and scan requests in MongoDB, dispatches jobs through Redis and BullMQ, and records their progress. It also includes a reproducible TLS laboratory and an English React interface.

The current worker runs in **orchestration_test** mode. Its result identifies the security sources awaiting implementation and ends as **partial**. TLS collection, risk findings and ML scoring are planned capabilities.

## Install and start

Clone the repository and copy `.env.example` to `.env`. The example authorizes `demo.example.com` for the local orchestration demonstration.

```sh
git clone https://github.com/liorma6/AI-security-agent-.git
cd AI-security-agent-
```

Use Docker with Compose v2 and Linux containers, then start the six-service stack.

```sh
docker compose up --build --wait
docker compose ps
```

Open [the application](http://127.0.0.1:5173). Its current page reports the API connection. Inspect service readiness at [API readiness](http://127.0.0.1:3001/ready) and [worker readiness](http://127.0.0.1:3002/ready). To stop the stack while retaining MongoDB and Redis data, run `docker compose down`. See the [runtime notes](docs/decisions/0001-runtime-and-local-environment.md) for the verified MongoDB host kernel.

## Submit an orchestration job

With the stack running and Node.js 24.22.2 installed, run the demonstration from the repository root.

```sh
npm run demo -- demo.example.com
```

It creates the authorized target, submits a scan, prints its ID and polls for the stored result. The result has `executionMode: "orchestration_test"`, `status: "partial"` and a reason for each unmeasured source.

| Operation | Behavior |
| --- | --- |
| POST /api/assets | Normalize an authorized hostname or root URL and return the stored asset. |
| GET /api/assets | List assets with limit (1–100) and cursor pagination. |
| POST /api/scans | Persist a request, return HTTP 202 and a Location header. |
| GET /api/scans/{scanId} | Read queued, running, partial or failed state and timestamps. |
| GET /health and /api/health | Read API liveness and capability flags. |
| GET /ready | Check MongoDB and Redis availability. |

Pass an `Idempotency-Key` header to POST /api/scans when retrying the same request. Reusing a key for a different asset returns 409. If Redis is unavailable, accepted requests stay in MongoDB and the dispatcher retries. A storage failure returns 503. [API contract](packages/contracts/openapi.json).

## Configuration

Both the API and worker use the same exact-hostname allowlist. Set `ALLOWED_TARGETS` in `.env` and restart the affected processes after a change. Authorization is checked at submission and again by the worker.

| Setting | Default or purpose |
| --- | --- |
| APP_MODE | Source mode defaults to bootstrap. Set orchestration_test for storage and queue processing. Compose enables orchestration_test. |
| ALLOWED_TARGETS | Empty denies all targets. The example file lists demo.example.com. |
| MONGO_URL / MONGO_DATABASE | Source defaults to mongodb://127.0.0.1:27017 and ai_security. |
| REDIS_URL / QUEUE_NAME | Source defaults to redis://127.0.0.1:6379 and scans. |
| WEB_PORT / API_PORT | Default host ports 5173 / 3001. |
| SCANNER_PORT / ML_PORT | Default host ports 3002 / 8000. |

Choose distinct free application ports. Compose publishes them on loopback and connects to MongoDB and Redis by internal service name. Bootstrap mode supports interface development with four application processes. Use /ready to distinguish a working process from available storage and queue dependencies.

## Run application processes from source

Use Node.js 24.22.2, npm 11.19.1 and uv 0.13.1. uv installs the pinned Python 3.13.16 environment. First start only the storage services with the development port mappings, then install and run the application.

```sh
docker compose -f compose.yaml -f compose.development.yaml up -d --wait mongo redis
npm ci
uv sync --project services/ml --frozen
npm run dev
```

With the example `.env`, this connects to the local storage ports and runs the full orchestration path. Press Ctrl+C to stop the application processes. Stop the development storage using `docker compose -f compose.yaml -f compose.development.yaml down`. On Windows, use `npm.cmd` if PowerShell restricts `npm.ps1`.

## TLS laboratory

Install the source dependencies and OpenSSL 3.x. Put openssl on PATH or set OPENSSL_BIN to its executable.

```sh
npm run test:lab
npm run lab
```

The lab creates fresh certificates and isolated loopback listeners. It covers expired and future certificates, hostname mismatch, chain errors, explicit private trust, legacy protocols, redirects, HSTS and timeout. The interactive command prints endpoints and stops with Ctrl+C. [Lab guide](tests/fixtures/tls/README.md).

## Checks and troubleshooting

Run checks after installing dependencies. Keep application ports free for smoke and browser checks.

```sh
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
```

Run `npm run test:integration` with MongoDB and Redis reachable through MONGO_URL and REDIS_URL, or their localhost defaults. It creates an isolated temporary database and queue, starts separate API/worker processes, injects connection and process failures and removes its test data. Tests cover concurrent retries, API restarts, duplicate job delivery, worker crashes, queue outages and authorization revocation. They use the full persistence path. CI runs them with real containers.

For a running Compose stack, run `npm run smoke:stack`. If a request stays queued, inspect /ready and `docker compose logs api scanner redis mongo`. A 403 means the exact normalized hostname needs approval in ALLOWED_TARGETS. After changing Compose configuration, run `docker compose up -d --build`.

## Documentation

- [System specification](docs/specification.md)
- [Architecture and recovery design](docs/architecture.md)
- [API and data contracts](packages/contracts/README.md)
- [TLS rules](docs/rules-and-policy.md)
- [Finding labeling guide](docs/labeling-guide.md)
