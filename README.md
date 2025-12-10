# DistributedAI Event Mesh

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