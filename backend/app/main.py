"""VANTYX FastAPI Application Entrypoint.

Configures CORS, centralized exception handling, lifespan event logging,
and versioned routing under a modular monolith architecture.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.schemas.error import ErrorItem, ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for initialization and graceful teardown."""
    logger.info(f"Initializing {settings.PROJECT_NAME} backend in [{settings.ENVIRONMENT}] environment")
    logger.info(f"Loaded CORS origins: {settings.CORS_ORIGINS}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} backend gracefully")


def create_application() -> FastAPI:
    """Application factory for VANTYX FastAPI backend."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Autonomous Media Intelligence Platform — Core API",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # 1. CORS Configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. Centralized Exception Handling
    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle standard HTTP exceptions with uniform structure."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorItem(
                    code=f"HTTP_{exc.status_code}",
                    message=str(exc.detail),
                ),
            ).model_dump(),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle schema and request payload validation failures."""
        logger.warning(f"Request validation failure on path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                success=False,
                error=ErrorItem(
                    code="VALIDATION_ERROR",
                    message="Request payload or parameters failed validation",
                ),
                details=exc.errors(),
            ).model_dump(),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors securely without leaking internal stack details."""
        logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorItem(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected internal server error occurred. Please try again later.",
                ),
            ).model_dump(),
        )

    # 3. Root Information Endpoint
    @application.get("/", tags=["System"])
    async def root_info():
        return {
            "name": settings.PROJECT_NAME,
            "tagline": "The intelligence behind every moment.",
            "status": "operational",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
        }

    # 4. Versioned API Router
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()
