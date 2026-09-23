# Application knowledge base

**Purpose:** a fact-based inventory of the current Stakeholder Dashboard, used as
the starting point for infrastructure decisions.  This describes implemented
behavior, not a future-state design.

**Last reviewed:** 2026-09-11

## Product and workload profile

The product is an internal account-intelligence workspace.  It combines
stakeholder relationship management, account and pod operations, executive
analytics, workforce/resourcing workflows, documents, and operational trust
views.  It is a stateful line-of-business application rather than a static
reporting site.

The API exposes 92 REST endpoints.  The workload is request/response oriented:
browser reads and governed CRUD operations.  There are no implemented
WebSockets, queues, background workers, scheduled jobs, external delivery
adapters, or live source-system connectors.

## Application components

| Component | Implementation | Operational characteristic |
| --- | --- | --- |
| Web client | React 19 single-page app, built with Vite and served by Nginx | Stateless, static assets plus same-origin API calls |
| API | Python 3.13, FastAPI, Uvicorn, SQLAlchemy | Stateless across requests except for its in-process hydrated repository/cache; horizontally runnable when backed by shared services |
| Relational data | PostgreSQL via `psycopg` and Alembic migrations | Production system of record; schema is normalized and includes cross-domain foreign-key integrity |
| File data | API streams uploads/downloads to a filesystem path | Private, durable shared storage is mandatory in production; supported files are limited to 25 MB |
| Container images | Separate web and API Dockerfiles | Suitable for immutable image deployment |

## Data and governance

PostgreSQL holds the canonical account, stakeholder, meeting, opportunity,
engagement, employee, executive, resourcing, audit, and provenance records.
The application requires PostgreSQL in production, will not create its schema
or seed business data there, and uses Alembic as the supported migration path.

The API applies role- and scope-based authorization.  Its implemented production
mode is `trusted_proxy`: an upstream identity gateway must strip user-supplied
identity headers, authenticate the user, and inject the verified identity and a
shared proxy secret.  Mutations create durable audit records; several commands
also support idempotent replay.

Uploads are written directly by the API to `UPLOAD_ROOT`; document metadata is
stored in PostgreSQL.  The application currently supports only the filesystem
storage backend.  The deployment must provide malware scanning, retention,
backup, and disaster recovery controls.  A SharePoint URL may be recorded as
metadata, but there is no SharePoint storage integration.

## Integration and asynchronous-work status

Executive data imports are implemented as a command-line, idempotent batch
import (`python -m app.manage import-executive`) with a dry-run mode and
reconciliation endpoint.  Imports are not automatically scheduled.  The
notification digest is an in-app API feed only; no outbound Teams or email
delivery is active.  This means the current application does not justify an
always-on worker fleet, Redis, Kafka, or a workflow engine.

## Existing AWS baseline

`infra/aws/ecs-fargate.yaml` already defines an initial production baseline:

- public HTTPS Application Load Balancer, with `/api/*` sent to the API service;
- two private ECS/Fargate services (web and API), with defaults of two tasks
  each;
- ECR repositories with immutable tags and scan-on-push;
- CloudWatch log groups with 90-day retention and ECS Container Insights;
- encrypted EFS with backups and an access point for shared document uploads;
- ECS migration task definition for `alembic upgrade head`;
- Secrets Manager references for the PostgreSQL URL and trusted-proxy secret.

The template intentionally expects an existing VPC, two public and two private
subnets, private-subnet egress, ACM certificate, RDS PostgreSQL, and an approved
identity gateway.  It does not provision the database, authentication gateway,
DNS, WAF, autoscaling, alarms, CI/CD, malware scanning, or a private ingress
pattern.

## Reliability and security signals already in the code

- Liveness and readiness endpoints; readiness checks database, migration state,
  and storage.
- Structured request-completion logs and request IDs.
- Controlled API errors, input validation, parameterized database access,
  CORS configuration, and browser security headers.
- Production startup guards for PostgreSQL, migrated/non-empty canonical data,
  trusted authentication, and durable document storage.
- Reconciliation endpoint intended as a release/import gate.
- Unit, integration, API, browser E2E, and visual test suites.

## Constraints that shape AWS design

1. The API and database are the authoritative operational tier; no CDN-only or
   serverless-static-site architecture can serve the full application alone.
2. Documents require shared private durable storage today because the API reads
   and writes local filesystem paths.  Replacing EFS with S3 requires an
   application change, not an infrastructure toggle.
3. The trusted-proxy authentication contract needs an identity-aware component
   in front of the API and must not be bypassable through a public origin path.
4. Database migrations must run once per release as a separately controlled
   task before application rollout.
5. Future imports, scanning, and notifications are asynchronous workload
   candidates, but should be introduced only when those capabilities are
   implemented and approved.

## Source evidence

- `backend/README.md`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/docs/EXECUTIVE_IMPORT.md`
- `infra/aws/ecs-fargate.yaml`
- `infra/docs/ARCHITECTURE.md`
- `infra/docs/OPERATIONS.md`
