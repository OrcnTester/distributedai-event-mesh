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
