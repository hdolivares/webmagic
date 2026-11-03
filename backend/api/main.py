"""
Main FastAPI application for WebMagic.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app (interactive API docs are only exposed in DEBUG mode)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors without echoing request bodies (they may contain passwords)."""
    errors = jsonable_encoder(exc.errors(), exclude={"input"})
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": errors},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.API_VERSION,
    }


# Import and include routers
from api.v1.router import api_router
from api.redirect import router as redirect_router
from api.v1 import generated_preview

app.include_router(redirect_router)  # Public short-link redirect — no prefix
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")

# Mount generated site preview router (serves {SITES_BASE_URL}/{subdomain})
# This must be mounted AFTER other routers to avoid catching API routes
app.include_router(generated_preview.router)
