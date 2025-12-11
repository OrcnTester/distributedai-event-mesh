# DistributedAI Event Mesh

- Event-driven microservices (Go)  
- Kafka / Redpanda  
- AI Gateway (FastAPI)  
- Vector DB (Qdrant)  
- Multi-tenant isolation  
- JWT-like auth + middleware design
- Rate-limiting per Tenant
- Prometheus metric-endpoint
- Semantic search

## Auth / JWT Simulation

For local development, the system uses a very simple dev token format instead of real JWTs:

```http
Authorization: Bearer tenant-a:user-123
```

 -tenant-a → treated as the tenant identifier
 -user-123 → treated as the user id

-user-service wraps protected routes with a tenantMiddleware that:

 -Parses the Authorization header
 -Extracts tenant + user info
 -Attaches them to the request context

ai-gateway uses a FastAPI dependency (get_tenant_context) to do the same thing.

In a real system, this would be replaced by proper JWT verification (signature, expiry, claims, etc.), but the overall architecture and middleware boundaries would remain the same.

## Multitenancy Model

This project simulates a simple multitenant architecture:

- Each request to `user-service` carries a `X-Tenant-Id` header.
- `POST /users/create` reads the tenant id, attaches it to the user entity, and publishes it in the `user.events` Kafka topic.
- `ai-gateway` consumes `user.events`, generates embeddings, and stores them in Qdrant with:
  - `tenantId`
  - `userId`
  - `email`
  - `name`

Qdrant uses a single `user_embeddings` collection, but queries are always filtered by `tenantId`:

```http
GET /ai/users/search?tenant_id=tenant-a&query=alice
```

This returns only users that belong to tenant-a, even if other tenants' data is stored in the same collection.

The same pattern can be extended to:

JWT claims (e.g. tenant_id in access tokens),

per-tenant rate limiting,

per-tenant configuration and quotas.

## Phase 2 – AI Enrichment & Vector Search

In phase 2, `ai-gateway` consumes `user.events` from Redpanda (Kafka), generates deterministic demo embeddings, and stores them in Qdrant (vector DB).

- `POST /users/create` (user-service)  
  → publishes a `user.events` message to Redpanda  
  → consumed by `ai-gateway`  
  → embedding stored in `user_embeddings` collection in Qdrant.

- `GET /ai/users/search?query=...`  
  → generates an embedding for the query  
  → performs vector similarity search in Qdrant  
  → returns the closest matching users with scores.

This phase demonstrates how AI/LLM-style semantic search can be attached to an event-driven microservice architecture.


An experimental backend playground for building AI-powered, event-driven, multi-tenant systems.

## Services

- `user-service` (Go)  
  Simple user microservice exposed over HTTP (will later publish events to Kafka).

- `ai-gateway` (Python / FastAPI)  
  Thin AI gateway layer (LLM calls, embeddings, agent orchestration).

## How to Run (Local Docker)

```bash
cd infra/docker
docker-compose up --build
```
Then:

http://localhost:8081/health
 → user-service

http://localhost:8090/health
 → ai-gateway


## 🚀 Deploying to Amazon EKS with Terraform

This project includes a lightweight but production-inspired IaC setup for deploying the entire **DistributedAI Event Mesh** architecture to **Amazon EKS** using Terraform.  
It provisions:

- VPC (public + private subnets)  
- NAT gateway  
- EKS cluster + managed node groups  
- AWS-configured networking for Kubernetes workloads  
- S3/DynamoDB Terraform state backend (optional)  
- Full compatibility for deploying the Kubernetes manifests in `infra/k8s/base/`  

### 1. Prerequisites

Before deploying to AWS:

- Terraform ≥ **1.5**
- AWS CLI configured (`aws configure`)
- kubectl installed
- An S3 bucket for Terraform state (optional but recommended)

Example S3 setup:

```bash
aws s3 mb s3://distributedai-terraform-state --region eu-central-1
aws dynamodb create-table   --table-name distributedai-terraform-locks   --attribute-definitions AttributeName=LockID,AttributeType=S   --key-schema AttributeName=LockID,KeyType=HASH   --billing-mode PAY_PER_REQUEST   --region eu-central-1
```

### 2. Terraform Folder Structure

```bash
infra/
  terraform/
    providers.tf
    main.tf
    variables.tf
    outputs.tf
```

The Terraform config handles:

- VPC creation  
- Subnet tagging for Kubernetes load balancers  
- Managed node groups  
- Control plane logs  
- IRSA (IAM Roles for Service Accounts)  

### 3. Initializing Terraform

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

This will:

- Create the VPC  
- Create the subnets  
- Launch an EKS control plane  
- Create a managed node group (default size: 2× t3.large)  

### 4. Configuring kubectl

After apply completes, update kubeconfig:

```bash
aws eks update-kubeconfig --name distributedai-eks --region eu-central-1
kubectl get nodes
```

You should now see your EKS worker nodes.

### 5. Deploying Kubernetes Workloads

Apply the Kubernetes manifests packaged under `infra/k8s/base/`:

```bash
kubectl apply -f infra/k8s/base/namespace.yaml
kubectl apply -f infra/k8s/base/
```

Verify pods and services:

```bash
kubectl get pods -n distributedai
kubectl get svc  -n distributedai
```

At this point, the following components are running inside your EKS cluster:

- **user-service** (Go)
- **ai-gateway** (FastAPI)
- **qdrant** (StatefulSet with persistent volume)
- **redis** (rate limiting)
- **redpanda** (Kafka-compatible event mesh)

### 6. Local → Cloud Parity

| Component         | Local (Docker Compose) | Cloud (EKS) |
|------------------|------------------------|-------------|
| Go user-service  | container              | Deployment |
| FastAPI gateway  | container              | Deployment |
| Kafka (Redpanda) | container              | Deployment |
| Qdrant           | container              | StatefulSet |
| Redis            | container              | Deployment |
| Networking       | Docker network         | VPC + Subnets |

This ensures a **consistent development → staging → production workflow**.

### 7. Destroying the Cluster

```bash
cd infra/terraform
terraform destroy
```

> ⚠️ Warning: This removes the entire VPC + EKS cluster.

