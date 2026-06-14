from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.coherence.router import router as coherence_router
from app.constructor.router import router as constructor_router
from app.verification.router import router as verification_router

app = FastAPI(title="Velvyko API")
app.include_router(auth_router)
app.include_router(constructor_router)
app.include_router(coherence_router)
app.include_router(verification_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
