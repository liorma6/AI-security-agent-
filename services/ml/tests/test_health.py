import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def request(method, path):
    async def send():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path)

    return asyncio.run(send())


def test_liveness_does_not_claim_model_readiness():
    response = request("GET", "/health")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["service"] == "ml"
    assert response.json()["modelLoaded"] is False
    assert response.json()["capabilities"]["inference"] is False


def test_prediction_is_not_exposed_before_implementation():
    assert request("POST", "/predict").status_code == 404
