# Morgan Stanley Account Intelligence API

FastAPI and SQLAlchemy backend for the connected Executive, Pod, Stakeholder, Meeting, Opportunity, Engagement, and Workforce experiences.

## Canonical data architecture

PostgreSQL is the required production authority. The API cache is hydrated from normalized tables at startup; it is not persisted as an application snapshot. A legacy `repository_snapshots` row is read only once when upgrading a prototype database, then copied transactionally into normalized tables.

The core lineage is:

```text
accounts -> pods -> divisions -> business_units
                              -> stakeholder_assignments -> stakeholders
stakeholders <-> meetings
meetings <-> opportunities
stakeholders <-> capco_employees (effective-dated relationship ownership)
stakeholders <-> opportunities <-> capco_employees -> executive_engagements
capco_employees <-> engagement_assignments -> executive_engagements
executive_engagements <-> stakeholders
executive_engagements -> revenue_records / engagement_milestones / resource_demand
```

Pod operating records and Executive analytics reference the same stakeholder, meeting, opportunity, engagement, employee, and pod identifiers. Foreign keys for these cross-domain references are installed by the PostgreSQL integrity migration.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m alembic -c alembic.ini upgrade head
python -m uvicorn backend.main:app --reload --port 8000
```

Development defaults to `backend/stakeholder-dev.db` only when `DATABASE_URL` is absent. Demo records are enabled by default in development so the product remains usable locally. Set `SEED_DEMO_DATA=false` to validate an empty or externally loaded database.

The backend loads the workspace-root `.env` itself; VS Code terminal environment injection is not required. `.env` is gitignored. URL-encode special characters in database passwords.

## Production configuration

Production must set:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
STAKEHOLDER_REPOSITORY=database
REQUIRE_DATABASE=true
SEED_DEMO_DATA=false
AUTO_CREATE_SCHEMA=false
API_CORS_ORIGINS=https://approved-ui.example.com
UPLOAD_ROOT=/durable/private/document/storage
DOCUMENT_STORAGE_BACKEND=filesystem
DOCUMENT_STORAGE_DURABLE=true
AUTH_MODE=trusted_proxy
TRUSTED_PROXY_SECRET=<long random gateway-to-api secret>
AI_PROVIDER=local
AI_MAX_SOURCES=8
```

Production startup fails when PostgreSQL is unavailable, when the canonical schema has not been migrated, when the database is empty, when an in-memory repository is selected, when authenticated-proxy configuration is absent, when durable upload storage is not explicitly configured, or when localhost CORS origins are configured. Startup never creates schema or inserts demo data in this mode.

The trusted identity proxy must remove client-supplied identity headers and set `X-Auth-Proxy-Secret`, `X-User-Subject`, `X-User-Roles`, and optionally `X-User-Employee-ID`. Supported roles are Reader, Editor, Account Manager, and Account Admin. Mutation responses include durable audit and request IDs.

## Migrations

Alembic is the only supported schema deployment mechanism:

```powershell
python -m alembic -c alembic.ini upgrade head
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini check
```

`schema.sql` was removed because it used UUID columns that were incompatible with the application's governed string identifiers and could create a second, disconnected schema.

For a database created by the earlier snapshot prototype, import before upgrading:

```powershell
python -m backend.manage import-legacy
python -m alembic -c alembic.ini upgrade head
```

The cleanup migration refuses to remove the legacy snapshot unless canonical stakeholder rows exist.

## Canonical metric definitions

- Revenue: sum of dated `revenue_records.amount` for active engagements in the selected period.
- Weighted pipeline: sum of canonical active opportunity value multiplied by persisted probability.
- Utilization: billable allocated hours divided by available capacity hours for employees with capacity records.
- Delivery on-time rate: completed or on-track engagement milestones divided by milestones due in the selected period.
- Capacity gap: qualified available FTE minus open 60-day resource demand.
- Relationship attention: strategic stakeholder contact recency plus persisted relationship strength; unknown data is not converted to zero.

Definitions and inputs are returned in Executive and Pod responses. Recommendations are deterministic findings with supporting metrics, source periods, related entity IDs, suggested actions, and confidence statements.

## Validation

Run all backend checks:

```powershell
python -m unittest discover -s backend -p "test_*.py" -v
```

With `DATABASE_URL` pointing to PostgreSQL, also run the database-specific
constraint and migration-head checks:

```powershell
python -m unittest backend.test_postgresql_integration -v
python -m alembic -c alembic.ini check
```

Run a cross-screen reconciliation against the configured database:

```text
GET /api/integrity/reconciliation
```

The response validates account and per-pod pipeline totals, weighted pipeline, canonical meeting-to-calendar links, employee relationship joins, project scope/sponsor/opportunity references, pod references, and workforce utilization lineage. A deployment should not proceed unless `status` is `passed`.

## Security boundary

The API validates domain inputs and document extensions/sizes, uses parameterized SQLAlchemy statements, returns controlled domain errors, enforces role-based writes, records mutation audit events, and keeps CORS environment-specific. The trusted-proxy mode is the application half of SSO: production still requires a correctly configured corporate identity gateway. Filesystem uploads must be placed on private durable storage; malware scanning, retention, backup, TLS termination, and disaster recovery remain deployment responsibilities.

## Grounded account assistant

The global assistant uses the same PostgreSQL account model as every screen. It retrieves current stakeholders, meetings, notes, opportunities, engagements, employees, tasks, critical items, milestones, and canonical Executive metrics directly from their governed records. Uploaded PDF, DOCX, XLSX/XLSM, PPTX, text, CSV, RTF, and EML content is extracted into `assistant_document_chunks`; each chunk retains a foreign key to `stakeholder_documents`. Legacy binary Office files, images, and scanned PDFs remain visible as document metadata but require conversion or OCR before their contents can be retrieved.

Conversations and citations are stored in `assistant_conversations` and `assistant_messages` and are isolated by authenticated subject. Readers may ask questions, while document reindexing is restricted to Account Admin. The assistant refuses questions with no relevant Morgan Stanley account evidence and does not use web search.

The safe default is `AI_PROVIDER=local`, which produces extractive grounded answers without sending account data outside the application. Model-generated answers are opt-in:

```text
AI_PROVIDER=openai
AI_MODEL=<enterprise-approved-model-id>
OPENAI_API_KEY=<secret>
AI_EXTERNAL_DATA_APPROVED=true
```

Only retrieved excerpts are sent, provider response storage is disabled, and the API key is never exposed to the browser. Enterprise legal, privacy, data-residency, and vendor approval is still required before enabling an external provider for client or commercial data.
