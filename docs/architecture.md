# DistributedAI Event Mesh – Architecture Overview

This document describes the high-level system architecture of the **DistributedAI Event Mesh**, a research-grade backend designed to explore:

- Event-driven microservices  
- Multi-tenant SaaS patterns  
- AI enrichment pipelines  
- Vector search (semantic search)  
- Streaming systems (Kafka / Redpanda)  
- Cross-service communication  
- Scalable API boundaries  

The goal is to simulate a **modern AI platform backend** using lightweight services that can be deployed locally or extended to cloud infrastructure (Kubernetes, Terraform, etc.).

## High-Level Diagram

```mermaid
flowchart LR
    subgraph Client["Client Apps"]
        A1["REST Calls (Bearer tenant:user)"]
    end

    subgraph UserService["user-service (Go)"]
        US1["/users"]
        US2["/users/create"]
        US3["tenantMiddleware()"]
    end

    subgraph Kafka["Redpanda (Kafka API)"]
        K1["Topic: user.events"]
    end

    subgraph AIGateway["ai-gateway (FastAPI)"]
        AI1["consume(user.events)"]
        AI2["generate_embedding()"]
        AI3["Qdrant upsert"]
        AI4["/ai/users/search"]
    end

    subgraph Qdrant["Vector DB"]
        Q1["Collection: user_embeddings"]
    end

    A1 --> US1
    A1 --> US2
    US2 -->|Publish user.events| K1
    K1 -->|AI Gateway Consumer| AI1
    AI1 --> AI2 --> AI3 --> Q1
    A1 --> AI4 --> Q1
```

## Components

### 1. **user-service (Go)**  
A stateless microservice responsible for:

- Serving tenant-scoped REST APIs  
- Creating users  
- Publishing domain events into Kafka  
- Enforcing multitenancy via middleware  
- Returning tenant-filtered lists  

#### Endpoints
| Endpoint | Description |
|---------|-------------|
| `GET /health` | No auth; service liveness |
| `GET /users` | Returns tenant-scoped user list |
| `POST /users/create` | Creates user + publishes `user.events` |

### 2. **Event Mesh (Redpanda / Kafka)**

- Streaming backbone  
- Decouples microservices  
- Powers asynchronous AI enrichment  

### 3. **ai-gateway (FastAPI)**  

Handles:
- Consuming `user.events`  
- Generating embeddings  
- Storing vectors in Qdrant  
- Semantic search  
- Tenant-aware API access  

### 4. **Qdrant Vector DB**

Stores embeddings with tenant-based payload filtering.

Example stored point:
```json
{
  "id": "tenant-a:123",
  "vector": [...],
  "payload": {
    "tenantId": "tenant-a",
    "userId": 123,
    "email": "alice@tenant-a.dev",
    "name": "Alice"
  }
}
```

Search queries always filter by tenant.

## Multitenancy Model

Two layers:

### 1. API Boundary Enforcement
Authorization header:
```
Bearer tenant-a:user-123
```
Parsed into tenant context.

### 2. Data-Layer Enforcement  
Qdrant payload filters ensure cross-tenant isolation even within a shared collection.

## Event Flow Summary

```mermaid
sequenceDiagram
    participant C as Client
    participant U as user-service
    participant R as Redpanda
    participant A as ai-gateway
    participant Q as Qdrant

    C->>U: POST /users/create (Bearer tenant-a:user-123)
    U->>U: middleware extracts tenantId + userId
    U->>R: Publish "user.events"
    R->>A: Deliver event
    A->>A: Generate embedding
    A->>Q: Upsert vector (tenant-scoped)
    C->>A: GET /ai/users/search?query=...
    A->>Q: Query vector with tenant filter
    Q->>A: Matching results
    A->>C: Tenant-scoped semantic search results
```

## Why This Architecture Matters

Demonstrates:
- Event-driven design  
- Multi-tenant architecture  
- AI/vector search integration  
- Extensible AI pipelines  
- Cloud-readiness  

## Next Steps

- Real embeddings (OpenAI, local models)  
- Per-tenant rate limits  
- K8s deployment  
- Terraform infra  
- Observability (Prom/Grafana)  
