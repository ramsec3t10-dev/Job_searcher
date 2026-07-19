# EMBEDHUNT AI — Autonomous Career Copilot

EMBEDHUNT AI is an autonomous agentic career copilot for embedded / systems engineers.
A candidate uploads a resume; the system understands the candidate, discovers jobs across
multiple sources, ranks and explains each match, surfaces skill gaps, builds a learning
roadmap, prepares interviews, and tracks applications — improving over time.

```
Resume ─▶ Understand ─▶ Discover ─▶ Rank ─▶ Explain ─▶ Gaps ─▶ Roadmap ─▶ Interview ─▶ Track ─▶ Learn
```

## Repository layout

| Path           | What it is                                                            |
| -------------- | --------------------------------------------------------------------- |
| `backend/`     | FastAPI + SQLAlchemy 2.0 async API, agent, recommendation engine      |
| `mobile/`      | Flutter client (auth, dashboard, recommendations, job detail)         |
| `deployment/`  | Docker, Kubernetes, nginx, Prometheus monitoring                      |
| `scripts/`     | DB init, seed data, PowerShell dev helpers                            |
| `docs/`        | Architecture, API reference, runbook                                  |
| `ai/`          | Parsing / embeddings / ranking assets and prompts                     |

## Quick start (backend)

Requires Python 3.12+ (verified on 3.14). From the repository root:

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r backend/requirements/base.txt -r backend/requirements/test.txt

# 3. Configure environment
Copy-Item backend/.env.example backend/.env   # then edit values

# 4. Initialise the database (SQLite works out of the box for local dev)
python scripts/init_db.py
python scripts/seed.py

# 5. Run the API
cd backend
uvicorn app.main:app --reload
```

The API is then available at <http://localhost:8000>:

- `GET /health`, `GET /health/ready` — liveness / readiness
- `GET /metrics` — Prometheus metrics
- `GET /docs` — interactive OpenAPI docs
- `POST /api/v1/auth/register` · `POST /api/v1/auth/login`

### Dev helper scripts (PowerShell)

```powershell
scripts/setup.ps1     # venv + install
scripts/run.ps1       # start API
scripts/test.ps1      # run the test suite
scripts/migrate.ps1   # apply Alembic migrations
```

## Tests

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

## Mobile (Flutter)

The Dart sources live in `mobile/lib` — a single Riverpod + go_router
architecture (state in `lib/state`, screens per feature under `lib/screens`,
design tokens in `lib/theme`). Fonts are bundled in `mobile/assets/google_fonts`
so first launch renders instantly and fully offline.

```powershell
cd mobile
flutter pub get
flutter analyze           # zero-tolerance: CI runs with --fatal-infos
flutter test              # runs mobile/test
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

> `10.0.2.2` reaches the host machine's `localhost` from the Android emulator.
> For a physical device or production, pass your API URL via `--dart-define`.

See [docs/architecture.md](docs/architecture.md) for design details,
[docs/api.md](docs/api.md) for the HTTP contract, and
[docs/runbook.md](docs/runbook.md) for deployment and operations.

## Deployment

```powershell
# Local stack (api + postgres + redis)
docker compose -f deployment/docker/docker-compose.yml up --build

# Kubernetes
kubectl apply -f deployment/kubernetes/
```

## License

Proprietary — internal project.
