"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as api_router

app = FastAPI(
    title="AIOS Req Engine",
    description="LangGraph-based requirements compilation and management service",
    version="0.1.0",
)

# Configure CORS
import os
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "https://aios-rtg.netlify.app",
]
# Add any additional origins from environment
extra_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins.extend([o.strip() for o in extra_origins if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"}, status_code=200)


# Include v1 API router
app.include_router(api_router, prefix="/v1", tags=["v1"])
