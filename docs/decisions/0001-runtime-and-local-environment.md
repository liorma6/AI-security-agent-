# Runtime and local environment

Decision recorded November 4, 2026.

| Component | Selected versions |
| --- | --- |
| JavaScript runtime and package manager | Node.js 24.22.2 and npm 11.19.1 |
| Python and environment manager | Python 3.13.16 and uv 0.13.1 |
| Application | Express 5.3.0, React 19.3.1, Vite 8.3.5 and FastAPI 0.162.0 |
| JavaScript checks | ESLint 10.14.0 with built-in JSX handling and React Hooks rules |
| Infrastructure | MongoDB 8.0.34, Redis 8.2.11 and nginx 1.30.6 |

The repository uses ECMAScript modules and plain Python. The supported Node release line and Python version were selected to match local development and the container images. The package and image versions were checked against their registries. The ML runtime will acquire training dependencies when model development begins.

Use `npm ci` and `uv sync --project services/ml --frozen` for reproducible installs. Change package declarations and lockfiles together. Source checks on Windows use isolated runtimes in the development workspace. Container checks run on GitHub-hosted Linux. Compose configures a local, single-operator deployment.

## MongoDB host compatibility

The first container run on Ubuntu 24.04 stopped during MongoDB startup on an incompatible kernel. The Compose job now uses Ubuntu 22.04 and logged a working kernel in the 6.8 series. The code and browser job uses Ubuntu 24.04. Check the actual host kernel when diagnosing startup failures, and revisit the runner choice when support changes. The stage 1 investigation identified a MongoDB 8.x incompatibility with kernels 6.19 through 7.0.13. [MongoDB 8.0 release notes](https://www.mongodb.com/docs/v8.0/release-notes/8.0/) and [stage 1 CI run](https://github.com/liorma6/AI-security-agent-/actions/runs/41848432558).

The images use version tags. Review upstream fixes and consider digest pinning for delivery. [Node.js release lines](https://nodejs.org/en/about/previous-releases), [Vite requirements](https://vite.dev/guide/) and [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).
