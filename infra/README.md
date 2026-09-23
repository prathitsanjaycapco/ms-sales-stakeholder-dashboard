# Stakeholder Dashboard infrastructure

This repository owns deployment infrastructure, the AWS ECS/Fargate stack, and the local integration composition. It does not contain application source or application Dockerfiles.

## Local integration workspace

Clone `frontend`, `backend`, and this repository as sibling directories, then run:

```powershell
docker compose -f infra/compose.yaml build api
docker compose -f infra/compose.yaml up -d database
docker compose -f infra/compose.yaml run --rm api python -m alembic upgrade head
docker compose -f infra/compose.yaml run --rm api python -m app.manage seed-demo
docker compose -f infra/compose.yaml up --build -d
```

Open `http://localhost:8080`. The Compose configuration is for local integration only; it deliberately uses development identity and PostgreSQL credentials.

## AWS production baseline

[`aws/ecs-fargate.yaml`](aws/ecs-fargate.yaml) deploys a public HTTPS Application Load Balancer, private ECS/Fargate services, ECR repositories, CloudWatch logs, and encrypted EFS storage for uploaded documents. It intentionally expects a pre-existing VPC, private subnets with egress, ACM certificate, RDS PostgreSQL, and Secrets Manager secrets.

Run migrations as a separate one-off ECS task using the API image before updating the API service. Do not enable demo seeding in production.

The API deliberately remains in `AUTH_MODE=trusted_proxy`. Before production traffic is allowed, place an approved identity gateway in front of the ALB that strips client-supplied identity headers and sets the API's documented trusted headers and shared secret. The stack does not weaken that boundary with a placeholder authentication mode.
