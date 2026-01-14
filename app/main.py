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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server (default)
        "http://localhost:3001",  # Alternative port
        "http://localhost:3002",  # Current workbench port
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "https://aios-rtg.netlify.app",  # Production frontend
        "https://*.netlify.app",  # Netlify preview deploys
    ],
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
