from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

USER_SERVICE_URL = "http://user-service:8081"


@app.get("/health")
def health():
    return {"status": "ai-gateway OK"}


@app.get("/ai/users/search")
async def search_users(query: str):
    """
    Şimdilik 'fake search':
    - user-service health'e ping atıyor (mesh bağlantısını test ediyoruz)
    - sonra tek user dönüyor: Alice
    """

    # 1) user-service ayakta mı, kontrol edelim
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{USER_SERVICE_URL}/health", timeout=2.0)
            resp.raise_for_status()
    except httpx.RequestError:
        # user-service hiç cevap veremedi
        raise HTTPException(status_code=502, detail="user-service unreachable")
    except httpx.HTTPStatusError as e:
        # 200 dönmedi vs.
        raise HTTPException(status_code=502, detail=f"user-service bad status: {e.response.status_code}")

    # 2) Şimdilik DB yok, fake user listesi üzerinden arama yapalım
    fake_user = {
        "email": "alice@orcun.dev",
        "name": "Alice Wonderland",
        "source": "fake-search",
    }

    q = query.lower()

    results = []
    if q in fake_user["email"].lower() or q in fake_user["name"].lower():
        results.append(fake_user)

    return {
        "query": query,
        "results": results,
        "total": len(results),
    }
