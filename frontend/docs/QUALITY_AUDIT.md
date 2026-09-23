# Quality audit and release gate

## Purpose

This is the release-quality evidence record for the account-intelligence workspace. All automated checks use seeded, disposable test data. They must never be pointed at production accounts, documents, or identity infrastructure.

## Required checks

| Area | Evidence | Gate |
| --- | --- | --- |
| Frontend behavior | Vitest component, routing, API-client, and accessibility-hook tests | `npm run test:unit` |
| Backend contracts and data integrity | FastAPI, repository, migration, governance, import, and cross-screen workflow tests | Backend repository CI: `python -m unittest discover -s tests -p "test_*.py"` |
| Browser workflows | Stakeholder map controls; meeting drawer scrolling and keyboard dismissal; resourcing lifecycle | `npm run test:e2e` against a separately running API or the infrastructure Compose stack |
| Responsive visual behavior | Desktop, wide desktop, tablet, and phone snapshots | `npm run test:visual` |
| Build and schema | Production Vite build and migration-head validation | Frontend `npm run build`; backend `python -m alembic check` |
| Production-like readiness | Seeded PostgreSQL readiness and reconciliation | `/api/health/ready`, `/api/integrity/reconciliation` |
| Supply chain and syntax | High-severity Node audit, Python dependency audit, dependency consistency, backend compilation | Frontend and backend CI security jobs |
| Delivery artifacts | API and web image builds | The application repositories' CI container builds |

The backend workflow supplies an isolated PostgreSQL service, applies migrations, and seeds the demo dataset before API tests. Cross-repository browser tests run through an integration environment managed by the infrastructure repository.

## Route-to-client coverage matrix

| Client/domain surface | Backend contract and linkage evidence |
| --- | --- |
| Session, health, trust, audit, search, notifications | Governed identity/session responses, readiness, reconciliation, and Operations Center tests |
| Stakeholders, reporting hierarchy, notes, documents | Repository/API validation, profile-map linkage, ownership history, upload/download and deletion tests |
| Meetings, tasks, critical items, pod focus | Pod store workflow tests plus calendar/profile/dashboard reconciliation and browser meeting-drawer coverage |
| Opportunities, engagements, executive analytics | Executive store and API workflow tests verify sponsor, opportunity, team, milestone, revenue, and risk IDs across views |
| Resource requirements, candidates, offers, onboarding, trash | Store and browser lifecycle tests verify state transitions, optimistic concurrency, archival, restoration, and project linkage |

Every new `api` client method must add one success-path and one relevant error, scope, or validation test in its owning domain. Every new cross-domain write must assert its dependent view-model and reconciliation result.

## Findings and remediation

| Finding | Severity | Resolution | Regression evidence |
| --- | --- | --- | --- |
| Stakeholder map opened too tightly framed | Medium | Default zoom is 80%; Reset restores 80% | Browser and visual map checks |
| Pod meeting drawer could expand beyond the viewport and lose its scrollbar | High | Drawer is fixed to the viewport with a stable independent scrollbar | Browser geometry/scroll check |
| Meeting drawer lacked the shared keyboard focus and Escape behavior | High | Uses `useDialogAccessibility` | Browser focus and Escape check |
| Explicit Pod View meeting deep links were intercepted by Account Data routing | High | Explicit `section=pod` now retains the Pod View route and resolves either display or canonical meeting IDs | Browser deep-link check |
| Visual test asserted the retired 100% map default | Medium | Updated to the 80% default and 71% zoom-out expectation | Visual test |

No unresolved Critical or High application defects are accepted at release. Lower-priority items require an owner, rationale, and target date in this table.

## External release-owner checks

The following are deployment controls and cannot be truthfully certified by a local test run: corporate SSO gateway header stripping, TLS termination, malware scanning and document quarantine, secret-manager wiring, durable-backup restoration, production telemetry/alert delivery, and live source-feed freshness. The release owner must verify these controls, then record the deployment date, environment, reconciliation result, and approver here before production rollout.
