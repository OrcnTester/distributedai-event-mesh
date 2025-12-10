from fastapi import FastAPI
import httpx
import asyncio
import hashlib
from typing import List

import numpy as np
from aiokafka import AIOKafkaConsumer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

app = FastAPI()
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
EMBEDDING_DIM = 64  # küçük demo için yeter

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
COLLECTION_NAME = "user_embeddings"

def ensure_collection():
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qm.VectorParams(
                size=EMBEDDING_DIM,
                distance=qm.Distance.COSINE,
            ),
        )
def generate_embedding(text: str) -> List[float]:
    """
    Demo amaçlı, deterministic fake embedding üretir.
    Gerçekte burada OpenAI / başka bir model kullanılır.
    """
    # HASH → BYTES → NUMPY VECTOR
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Hash uzunluğunu EMBEDDING_DIM'e uydur
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
    if arr.shape[0] < EMBEDDING_DIM:
        arr = np.pad(arr, (0, EMBEDDING_DIM - arr.shape[0]))
    else:
        arr = arr[:EMBEDDING_DIM]
    # normalize
    norm = np.linalg.norm(arr)
    if norm == 0:
        return (arr).tolist()
    return (arr / norm).tolist()

@app.get("/health")
def health():
    return {"status": "ai-gateway OK"}


@app.get("/users/proxy")
async def proxy_users():
    """
    Simple proxy to user-service, later this will be the place where
    LLM reasoning or enrichment happens.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://user-service:8081/users")
        resp.raise_for_status()
        return resp.json()
    
import asyncio
from aiokafka import AIOKafkaConsumer

import json
from qdrant_client.http.models import PointStruct

async def consume_events():
    consumer = AIOKafkaConsumer(
        "user.events",
        bootstrap_servers="redpanda:9092",
        group_id="ai-gateway-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            raw = msg.value.decode()
            print("🔥 AI-Gateway received event:", raw)

            try:
                data = json.loads(raw)
                user_id = data.get("id")
                email = data.get("email", "")
                name = data.get("name", "")

                text = f"{name} <{email}>"
                emb = generate_embedding(text)

                qdrant.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=user_id,
                            vector=emb,
                            payload={
                                "email": email,
                                "name": name,
                            },
                        )
                    ],
                )
                print(f"💾 Stored embedding for user {user_id} in Qdrant.")
            except Exception as e:
                print("Error processing event:", e)

    finally:
        await consumer.stop()
@app.on_event("startup")
async def startup_event():
    ensure_collection()
    asyncio.create_task(consume_events())

from fastapi import Query

@app.get("/ai/users/search")
def search_users(query: str = Query(..., description="Search query")):
    emb = generate_embedding(query)

    search_result = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=emb,
        limit=5,
    )

    out = []
    for r in search_result:
        out.append({
            "user_id": r.id,
            "score": r.score,
            "email": r.payload.get("email"),
            "name": r.payload.get("name"),
        })

    return {
        "query": query,
        "results": out,
    }
