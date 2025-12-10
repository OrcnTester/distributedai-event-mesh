from fastapi import FastAPI
import httpx

app = FastAPI()


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

async def consume_events():
    consumer = AIOKafkaConsumer(
        "user.events",
        bootstrap_servers="redpanda:9092",
        group_id="ai-gateway-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print("🔥 AI-Gateway received event:", msg.value.decode())
    finally:
        await consumer.stop()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_events())
