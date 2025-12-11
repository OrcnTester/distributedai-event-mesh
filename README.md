# DistributedAI Event Mesh

- Event-driven microservices (Go)  
- Kafka / Redpanda  
- AI Gateway (FastAPI)  
- Vector DB (Qdrant)  
- Multi-tenant isolation  
- JWT-like auth + middleware design

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