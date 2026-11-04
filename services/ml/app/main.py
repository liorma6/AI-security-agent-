from fastapi import FastAPI, Response

app = FastAPI(title="AI Security Agent ML", version="0.1.0")


@app.get("/health")
def health(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "ok",
        "service": "ml",
        "version": "0.1.0",
        "stage": 1,
        "mode": "bootstrap",
        "capabilities": {"inference": False},
        "modelLoaded": False,
    }
