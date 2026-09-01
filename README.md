# Morgan Stanley account intelligence

Connected executive, pod, stakeholder, resourcing, onboarding, and governed account-data experiences backed by FastAPI, SQLAlchemy, PostgreSQL, React, and Vite.

See [Architecture](docs/ARCHITECTURE.md) for the production system overview and component/data-flow diagrams.

## Start locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
npm.cmd ci
Copy-Item .env.example .env
python -m alembic -c alembic.ini upgrade head
python -m backend.manage seed-demo
python -m uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```powershell
npm.cmd run dev
```

Open `http://localhost:5173`. Production must use PostgreSQL, an authenticated identity proxy, durable private document storage, and the strict configuration described in [backend/README.md](backend/README.md).

## Validate a release

```powershell
npm.cmd run test:ci
python -m alembic -c alembic.ini check
```

Before deployment, verify `GET /api/health/ready` is ready and `GET /api/integrity/reconciliation` is passed. The Settings → Trust & operations screen surfaces the same evidence, data freshness, audit history, and assistant index state.

## Deployment

Container definitions live in `deploy/`. Apply migrations as a separate release step before starting the API; never run schema creation or demo seeding in production. The web container expects an API service named `api`, though the nginx upstream should be adapted to the target platform.

See [OPERATIONS.md](docs/OPERATIONS.md) for backup, restoration, observability, file-security, and incident procedures.
