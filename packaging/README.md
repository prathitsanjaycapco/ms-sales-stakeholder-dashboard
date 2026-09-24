# Portable Windows build

The portable build packages the React frontend, FastAPI backend, Python runtime, migrations, and SQLite support into one Windows x64 folder. Recipient computers do not need Python, Node.js, Docker, or an installer.

## Build locally

Run from the repository root in 64-bit PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build-portable.ps1
```

The script installs build dependencies into `.portable-build-venv`, builds the frontend, creates the PyInstaller folder, and writes `artifacts/StakeholderDashboard-windows-x64.zip`.

The root `windows-portable` GitHub Actions workflow performs the same build on Windows and publishes the ZIP as a workflow artifact.

## Import contract

`packaging/windows/import-template.json` is the version 1 contract for data produced by the separate spreadsheet/LLM process. It accepts one account name plus custom pods, divisions, business units, Capco employees, client stakeholders, reporting lines, employee skills, and employee-to-stakeholder relationships.

IDs must be stable across generated files. Every referenced manager, division, business unit, employee, and stakeholder must exist in the same complete file. Each pod requires one stakeholder with the `Pod Head` role, reporting hierarchies must be acyclic, and each business unit can have at most one primary technology stakeholder.

Validation builds and checks a temporary migrated database without changing the active file. Import builds the same temporary database, backs up an existing `data/dashboard.db`, and atomically replaces it only after validation succeeds.
