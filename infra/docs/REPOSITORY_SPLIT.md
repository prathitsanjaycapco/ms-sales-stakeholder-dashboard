# Publishing the three repositories

The directories in this staging workspace are repository roots:

- `frontend/` — React application, UI tests, visual baselines, and its container image.
- `backend/` — FastAPI application, Alembic migrations, API tests, and its container image.
- `infra/` — AWS infrastructure, local integration Compose, and deployment operations.

Commit the reorganization in this workspace first. Then create three empty remote repositories and use `git filter-repo` to retain relevant history for each one:

```powershell
git clone --no-local <staging-repository> frontend-repo
Set-Location frontend-repo
git filter-repo --path frontend/ --path-rename frontend/:
```

Repeat with `backend/` and `infra/`, changing both path arguments. Add the matching remote and push the filtered repository. This preserves file history while removing unrelated application code from each repository.

The infrastructure repository expects its sibling checkouts to be named `frontend` and `backend` only for local Docker Compose integration. AWS deploys immutable ECR images and has no source-repository path dependency.
