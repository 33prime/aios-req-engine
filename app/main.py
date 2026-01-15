"""FastAPI application entry point."""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import router as api_router


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-Proto header for HTTPS behind proxy."""

    async def dispatch(self, request: Request, call_next):
        # Check X-Forwarded-Proto header to determine if request came via HTTPS
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if forwarded_proto == "https":
            # Update the scope to reflect HTTPS
            request.scope["scheme"] = "https"
        return await call_next(request)


app = FastAPI(
    title="AIOS Req Engine",
    description="LangGraph-based requirements compilation and management service",
    version="0.1.0",
)

# Add proxy headers middleware (must be before CORS)
app.add_middleware(ProxyHeadersMiddleware)

# Configure CORS
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
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
