# AWS infrastructure recommendation

**Decision:** use ECS on AWS Fargate as the production compute platform.  Keep
the current two-container-service pattern during the first production release;
do not introduce EKS, Lambda/API Gateway, Redis, or a worker platform yet.

This recommendation is based on the implemented application inventory in
[`APPLICATION_KNOWLEDGE_BASE.md`](APPLICATION_KNOWLEDGE_BASE.md).

## Diagrams

- [Target AWS architecture (SVG)](architecture/aws-target-architecture.svg) · [Mermaid source](architecture/aws-target-architecture.mmd)
- [Browser request and data flow (SVG)](architecture/aws-request-data-flow.svg) · [Mermaid source](architecture/aws-request-data-flow.mmd)

## Recommended initial production topology

```text
Corporate identity gateway / approved access layer
  -> AWS WAF
  -> Application Load Balancer (HTTPS, ACM, restricted ingress)
       -> ECS/Fargate web service (Nginx + React SPA)
       -> ECS/Fargate API service (FastAPI)
            -> Amazon RDS for PostgreSQL (private, Multi-AZ DB instance)
            -> Amazon EFS (private, encrypted document filesystem)
            -> AWS Secrets Manager / CloudWatch Logs

ECR -> ECS migration task -> API service rollout
```

Run at least two API tasks across Availability Zones.  The web service can also
run as two small tasks for availability, although it is a lower-risk component.
Start with the task allocations already encoded in the repository: API 0.5 vCPU
/ 1 GB and web 0.25 vCPU / 0.5 GB, then right-size from metrics.  Configure
autoscaling only after a baseline is available: API CPU, memory, ALB request
count/target, and p95 latency are useful signals.  Minimize initially at two
API tasks; do not allow scale-to-zero.

The existing `aws/ecs-fargate.yaml` is close to this design and should be
evolved rather than replaced.  It already implements the ALB routing, private
Fargate tasks, ECR, CloudWatch logs, EFS, secret injection, and a one-off
migration task.

## Why this is the appropriate fit

The application is a conventional containerized FastAPI service with a
relational system of record, synchronous uploads, and ordinary REST traffic.
Fargate removes node and Kubernetes operations while retaining long-running
processes, private VPC access, direct EFS mounting, and controlled migration
tasks.  Fargate uses `awsvpc` networking and ECS task definitions provide the
right deployment unit for these containers. [AWS ECS Fargate documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html)

RDS for PostgreSQL is the direct managed match for the existing SQLAlchemy,
Alembic, and PostgreSQL configuration.  Use an RDS Multi-AZ **DB instance** for
the initial availability requirement.  Its standby is for failover rather than
read traffic, which is sufficient before measured read pressure calls for a
reader-capable Multi-AZ DB cluster or read replica. [AWS RDS Multi-AZ documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)

EFS is appropriate only because the application presently needs a shared POSIX
filesystem mounted by multiple API tasks.  ECS can mount an EFS filesystem
using a task-definition volume and access point. [AWS EFS/ECS guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/create-an-amazon-ecs-task-definition-and-mount-a-file-system-on-ec2-instances-using-amazon-efs.html)

## Required production additions to the existing template

| Area | Add or change | Reason |
| --- | --- | --- |
| Access | Put the approved corporate identity gateway in the actual request path and restrict ALB ingress to it (or to its controlled network ranges). Keep the API service reachable only from the ALB. | The API accepts production identity only from a trusted proxy; an unrestricted alternative path would undermine the intended trust boundary. |
| Edge protection | Associate an AWS WAFv2 web ACL with the ALB, with managed baseline rules, rate limits, and application-specific allow/deny rules. | WAF web ACLs can be associated with ALBs. [AWS WAF documentation](https://docs.aws.amazon.com/waf/latest/developerguide/waf-anti-ddos-alb.html) |
| Network | Keep ECS and RDS private. Use VPC endpoints for ECR, CloudWatch Logs, Secrets Manager, and S3 where feasible; otherwise account for NAT egress. | Reduces the public attack surface and ongoing NAT dependency. |
| Database | Provision encrypted RDS PostgreSQL, automated backups/PITR, deletion protection, maintenance window, enhanced monitoring, and an RDS security group allowing 5432 only from API tasks. | The database is the authoritative business and audit store. |
| Secrets and encryption | Use Secrets Manager for database and proxy credentials; use KMS customer-managed keys where organizational policy requires them for RDS, EFS, logs, and secrets. | Removes credentials from images and centralizes rotation/audit. |
| Delivery | Build immutable images, scan them, push to ECR, run the migration ECS task exactly once, then deploy API and web from the same commit. Use a CI role with OIDC and least privilege. | Matches the existing release gate and prevents concurrent migrations. |
| Observability | Add CloudWatch alarms/dashboards for ALB 4xx/5xx, unhealthy targets, ECS task failures and saturation, RDS CPU/connections/storage/failover, EFS storage, migration failure, and reconciliation failure. Send security/audit logs to the approved central account. | The code already emits readiness, request IDs, and structured request completion logs. |
| Resilience | Configure backups and quarterly restore testing for RDS and EFS. Set retention from the defined RPO/RTO and data-retention policy. | Database metadata and document binaries must restore together. |

## Important document-security limitation

EFS is a compatibility choice, not the long-term preferred document architecture.
The API writes a file and then immediately creates its metadata; downloads are
permitted whenever the metadata and file exist.  Therefore infrastructure alone
cannot guarantee that an uploaded file is scanned before it becomes available.

Before real production documents are accepted, add an application-enforced
`pending/clean/quarantined` scan state and deny downloads until `clean`.  Then
choose one of these paths:

1. Keep EFS and scan synchronously in a controlled upload service before the
   file is committed; or
2. Move document binaries to S3, trigger scanning on object creation, and have
   the application authorize download only after scan completion.

Option 2 is the stronger long-term design, but it requires application changes
because the current code supports only a filesystem backend.  It should not be
represented as a simple replacement of EFS in infrastructure.

## What to defer

- **EKS:** adds cluster and platform operations without a demonstrated need for
  those controls.
- **Lambda/API Gateway:** would require adapting a large, stateful REST API,
  EFS uploads, database connection behavior, and migration workflow, with no
  clear benefit at this scale.
- **RDS Proxy:** consider when API autoscaling or connection churn is measured;
  it is not a required component for two small API tasks.
- **Redis, SQS, EventBridge Scheduler, Step Functions:** introduce them when
  scheduled imports, notifications, scanning, or other asynchronous work is
  actually enabled.
- **S3/CloudFront static frontend:** attractive later, but defer it while the
  same-origin trusted-proxy design is in place.  First redesign browser/API
  authentication so the API can validate standard user tokens or so the access
  layer can securely proxy both static assets and API calls.
- **Multi-region active/active:** not warranted until business continuity
  requirements define an RTO/RPO that a single-region Multi-AZ design cannot
  meet.

## Suggested adoption sequence

1. Establish a non-production AWS environment with the current ECS template,
   RDS PostgreSQL, EFS, secrets, and the real identity-gateway integration.
2. Add the required network restrictions, WAF, backups, alarms, CI/CD, and
   migration-release automation.
3. Resolve the malware-scan/download-gate application limitation before loading
   sensitive documents.
4. Load-test representative read, write, and 25 MB upload traffic; set database
   size, task size, connection limits, and autoscaling from evidence.
5. Conduct restore, failover, identity-boundary, and reconciliation exercises
   before production approval.
