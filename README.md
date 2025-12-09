# DistributedAI Event Mesh

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