"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import router as api_router

app = FastAPI(
    title="AIOS Req Engine",
    description="LangGraph-based requirements compilation and management service",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"}, status_code=200)


# Include v1 API router
app.include_router(api_router, prefix="/v1", tags=["v1"])
