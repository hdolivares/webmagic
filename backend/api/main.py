"""
Main FastAPI application for WebMagic.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:5173",  # Vite dev server
    ] if settings.DEBUG else [
        "https://admin.webmagic.com",
        "https://web.lavish.solutions",
        "https://sites.lavish.solutions",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log and handle validation errors with detailed information."""
    logger.error(f"❌ Validation error on {request.method} {request.url.path}")
    logger.error(f"   Errors: {exc.errors()}")
    logger.error(f"   Body: {exc.body if hasattr(exc, 'body') else 'N/A'}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body if hasattr(exc, 'body') else None},
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
        "docs": "/docs"
    }


# Import and include routers
from api.v1.router import api_router
from api.redirect import router as redirect_router
from api.v1 import generated_preview

app.include_router(redirect_router)  # Public short-link redirect — no prefix
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")

# Mount generated site preview router (serves sites.lavish.solutions/{subdomain})
# This must be mounted AFTER other routers to avoid catching API routes
app.include_router(generated_preview.router)
