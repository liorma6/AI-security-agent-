# AI Security Agent

AI Security Agent is a local application for developing an HTTPS and TLS assessment service. This bootstrap version runs a React interface, an Express API, a Node.js scanner process and a Python service. The interface reports API connectivity. Website scanning and ML scoring are planned capabilities.

```sh
git clone --branch stage/01-bootstrap https://github.com/liorma6/AI-security-agent-.git
cd AI-security-agent-
```

## Start with Docker

Use Docker with the Compose v2 plugin and Linux containers. Start the stack from the repository root.

```sh
docker compose up --build --wait
```

Open [the application](http://127.0.0.1:5173). The home page shows **Connected to the API** after a successful health request. To inspect the six services and then stop the stack while keeping its data volumes, use these commands.

```sh
docker compose ps
docker compose down
```

Compose starts the web interface, API, scanner service, ML service, MongoDB and Redis. The application ports bind to loopback. MongoDB and Redis use the internal Compose network. For the Linux kernel used to verify MongoDB startup, see the [runtime notes](docs/decisions/0001-runtime-and-local-environment.md).

## Run from source

Use Node.js 24.22.2, npm 11.19.1 and uv 0.13.1. The Python project pins Python 3.13.16. uv installs it if needed. Run these commands from the repository root.

```sh
npm ci
uv sync --project services/ml --frozen
npm run dev
```

Open [the application](http://127.0.0.1:5173). Press Ctrl+C in the terminal to stop all four processes. This mode runs with the default configuration and requires only the application processes. On Windows, use `npm.cmd` if PowerShell restricts `npm.ps1`.

## Configuration and health checks

To change ports, copy [.env.example](.env.example) to `.env` and set the values below. Choose four distinct, free ports. Run one stack at a time on the chosen ports.

| Component | Port setting | Default URL |
| --- | --- | --- |
| Web | `WEB_PORT` | http://127.0.0.1:5173 |
| Express API | `API_PORT` | http://127.0.0.1:3001/health |
| Scanner service | `SCANNER_PORT` | http://127.0.0.1:3002/health |
| Python ML service | `ML_PORT` | http://127.0.0.1:8000/health |

Open the API health URL to see `service: "api"`, `status: "ok"` and the current capability flags. The web server forwards `/api/health` to the same API. If the page shows **API unavailable**, check the API health URL and the API process output, or run `docker compose logs api web` for a container stack.

## Development checks

After installing from source, run the checks below with the application ports free. The smoke test starts the built web interface and the three backend services, checks their HTTP responses, and stops them.

```sh
npm run lint
npm test
uv run --project services/ml --frozen ruff check services/ml
uv run --project services/ml --frozen pytest services/ml
npm run build
npm run smoke
npx playwright install chromium
npm run test:web
```

To verify an already running Compose stack with Node.js, run `npm run smoke:stack`.

## Documentation

- [System specification](docs/specification.md)
- [Service architecture](docs/architecture.md)
