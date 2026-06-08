from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.constructor.router import router as constructor_router

app = FastAPI(title="Velvyko API")
app.include_router(auth_router)
app.include_router(constructor_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
