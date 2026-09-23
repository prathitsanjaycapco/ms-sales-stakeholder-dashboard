# Three-repository staging workspace

The codebase is organized into three independent repository roots:

- [`frontend`](frontend/README.md) — React application and UI tests.
- [`backend`](backend/README.md) — FastAPI API, migrations, and API tests.
- [`infra`](infra/README.md) — AWS ECS/Fargate infrastructure and local integration Compose.

See [`infra/docs/REPOSITORY_SPLIT.md`](infra/docs/REPOSITORY_SPLIT.md) to publish each directory as its own repository while preserving history.
