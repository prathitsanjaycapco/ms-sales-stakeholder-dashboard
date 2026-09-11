# Production operations

## Release gate

1. Back up PostgreSQL and the durable document store.
2. Run `alembic upgrade head` as a dedicated migration job.
3. Deploy the API and web artifacts built from the same commit.
4. Require `/api/health/ready` to return 200.
5. Require `/api/integrity/reconciliation` to report `passed`.
6. Confirm Settings → Trust & operations shows the expected repository, identity mode, storage durability, and source freshness.

## Identity and secrets

Terminate TLS and authenticate users at the corporate gateway. The gateway must remove client-supplied identity headers and set the trusted-proxy secret and scoped user headers documented in `backend/README.md`. Store database, proxy, and approved AI credentials in the platform secret manager; never bake them into images.

## Backup and restoration

- Take encrypted PostgreSQL backups at least daily and retain transaction logs according to the recovery-point objective.
- Back up `UPLOAD_ROOT` with the same retention boundary as its document metadata.
- Restore the database and document store to an isolated environment at least quarterly, then run migrations, readiness, reconciliation, and a sample document download.
- Treat an untested backup as unavailable.

## Documents

Place uploads in private durable storage. A production ingress or storage event must scan every upload for malware before it becomes downloadable. Quarantine failed or pending scans, log the decision, and apply legal retention/deletion policies to both the binary and database metadata.

## Observability

Collect structured API logs and preserve `X-Request-ID` through every proxy. Alert on readiness failures, elevated 5xx/409 rates, audit-persistence failures, database saturation, storage exhaustion, stale source feeds, and failed reconciliation. Browser errors should be sent only to an enterprise-approved telemetry service and must exclude client data.

## Notifications and integrations

`GET /api/notifications/digest` is the governed alert feed for in-app use and future approved delivery adapters. External delivery is deliberately disabled until a scheduler/service account, recipient policy, retry behavior, and Teams/email connector are approved. Source-system ingestion should write canonical identifiers, provenance, and synchronization timestamps and should be idempotent.

## Incident response

Disable writes at the identity gateway if integrity is uncertain, preserve database and audit evidence, record request IDs, restore only from a verified backup, and rerun reconciliation before reopening the workspace. Rotate any credential suspected of exposure.
