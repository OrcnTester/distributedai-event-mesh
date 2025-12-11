from fastapi import FastAPI, HTTPException
import httpx

import asyncio
import hashlib
from typing import List

import numpy as np
from aiokafka import AIOKafkaConsumer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

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


app = FastAPI()

USER_SERVICE_URL = "http://user-service:8081"


@app.get("/health")
def health():
    return {"status": "ai-gateway OK"}

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
                tenant_id = data.get("tenantId", "unknown")

                text = f"{name} <{email}>"
                emb = generate_embedding(text)

                qdrant.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=int(user_id),        # 🔥 ÖNEMLİ: artık "tenant-a:175" değil, 175
                            vector=emb,
                            payload={
                                "email": email,
                                "name": name,
                                "tenantId": tenant_id,      # multi-tenant bilgisi payload'ta
                                "userId": user_id,
                            },
                        )
                    ],
                )
                print(f"💾 Stored embedding for user {user_id} in Qdrant (tenant={tenant_id}).")
            except Exception as e:
                print("Error processing event:", e)

    finally:
        await consumer.stop()

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
    
from fastapi import Query, HTTPException

@app.get("/ai/users/search")
def search_users(
    tenant_id: str = Query(..., alias="tenant_id", description="Tenant identifier"),
    query: str = Query(..., description="Search query"),
):
    # 1) Query için embedding üret
    emb = generate_embedding(query)

    # 2) Qdrant search request body
    search_payload = {
        "vector": emb,
        "limit": 5,
        "with_payload": True,
        "filter": {
            "must": [
                {
                    "key": "tenantId",
                    "match": {"value": tenant_id},
                }
            ]
        },
    }

    # 3) Qdrant REST API'ye direkt httpx ile vur
    try:
        resp = httpx.post(
            f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{COLLECTION_NAME}/points/search",
            json=search_payload,
            timeout=5.0,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error talking to Qdrant: {e}",
        )

    if resp.status_code != 200:
        # Qdrant tarafında hata varsa, text olarak geri dönsün
        raise HTTPException(
            status_code=500,
            detail=f"Qdrant error: {resp.text}",
        )

    body = resp.json()
    points = body.get("result", []) or []

    # 4) Response'u sadeleştir
    results = []
    for point in points:
        payload = point.get("payload", {}) or {}
        results.append(
            {
                "user_id": payload.get("userId"),
                "tenant_id": payload.get("tenantId"),
                "score": point.get("score"),
                "email": payload.get("email"),
                "name": payload.get("name"),
            }
        )

    return {
        "tenant_id": tenant_id,
        "query": query,
        "results": results,
    }
