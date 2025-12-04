"""
FastAPI application for Nexus ECS Service.

Provides ML inference endpoints for control mapping:
- POST /embed - Generate embeddings
- POST /retrieve - Cosine similarity search
- POST /rerank - Cross-encoder reranking
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
import uuid
import asyncio

from nexus_ecs_service.app.routers import embed, retrieve, rerank
from nexus_ecs_service.app.startup import load_models_from_s3, cleanup_models, MODELS
from nexus_ecs_service.app.aws_logger import configure_cloudwatch_logging, StructuredLogger

# Configure CloudWatch logging
configure_cloudwatch_logging(
    service_name="nexus-ecs-service",
    log_level="INFO",
    enable_console=True
)
logger = StructuredLogger("nexus-ecs-service")

# Global state for tracking model loading
MODEL_LOADING_STATE = {
    "loading": False,
    "loaded": False,
    "error": None,
    "started_at": None,
}

# Create FastAPI app
app = FastAPI(
    title="Nexus ECS Service API",
    version="1.0.0",
    description="GPU ML inference service for control mapping - embedding, retrieval, and reranking",
    docs_url="/docs",
    redoc_url="/redoc"
)


async def _background_model_loader():
    """Background task to load models - runs concurrently with request handling."""
    global MODEL_LOADING_STATE

    try:
        MODEL_LOADING_STATE["loading"] = True
        MODEL_LOADING_STATE["started_at"] = time.time()

        logger.info("Background model loading started")
        await load_models_from_s3()

        MODEL_LOADING_STATE["loaded"] = True
        MODEL_LOADING_STATE["loading"] = False
        logger.info("Background model loading complete - service ready for inference")

    except Exception as e:
        MODEL_LOADING_STATE["error"] = str(e)
        MODEL_LOADING_STATE["loading"] = False
        logger.critical(
            "Background model loading failed",
            error_type=type(e).__name__,
            error_message=str(e)
        )


@app.on_event("startup")
async def startup_event():
    """Start model loading as background task."""
    logger.info("Application startup - creating background model loading task")

    asyncio.create_task(_background_model_loader())

    logger.info("Startup complete - server ready to accept requests, models loading in background")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Application shutdown initiated")
    cleanup_models()
    logger.info("Shutdown complete")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with execution time and request ID."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    # Skip logging for health checks to reduce noise
    if request.url.path not in ["/health", "/ready"]:
        logger.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            request_id=request_id
        )

    try:
        response = await call_next(request)

        execution_time_ms = int((time.time() - start_time) * 1000)

        if request.url.path not in ["/health", "/ready"]:
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                execution_time_ms=execution_time_ms,
                request_id=request_id
            )

        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )
        raise


@app.get("/health")
async def health_check():
    """
    Health check endpoint - ALWAYS returns 200 during startup.

    This allows ALB to mark the target as healthy while models load.
    Use /ready endpoint to check actual readiness for inference.
    """
    global MODEL_LOADING_STATE

    models_loaded = len(MODELS) > 0 and MODEL_LOADING_STATE.get("loaded", False)
    is_loading = MODEL_LOADING_STATE.get("loading", False)
    error = MODEL_LOADING_STATE.get("error")

    loading_time = None
    if MODEL_LOADING_STATE.get("started_at"):
        loading_time = int(time.time() - MODEL_LOADING_STATE["started_at"])

    if error:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": error,
                "models_loaded": False,
                "service": "nexus-ecs-service"
            }
        )

    if models_loaded:
        return {
            "status": "healthy",
            "models_loaded": True,
            "models": list(MODELS.keys()),
            "service": "nexus-ecs-service"
        }

    if is_loading:
        return {
            "status": "loading",
            "models_loaded": False,
            "loading_time_seconds": loading_time,
            "service": "nexus-ecs-service"
        }

    return {
        "status": "starting",
        "models_loaded": False,
        "service": "nexus-ecs-service"
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check - returns 200 only when models are loaded.
    Use this to check if service is ready to process requests.
    """
    global MODEL_LOADING_STATE

    models_loaded = len(MODELS) > 0 and MODEL_LOADING_STATE.get("loaded", False)

    if not models_loaded:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "models_loaded": False,
                "loading": MODEL_LOADING_STATE.get("loading", False),
                "service": "nexus-ecs-service"
            }
        )

    return {
        "status": "ready",
        "models_loaded": True,
        "models": list(MODELS.keys()),
        "service": "nexus-ecs-service"
    }


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "service": "Nexus ECS Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


# Include API routers
app.include_router(embed.router, prefix="/api/v1", tags=["Embedding"])
app.include_router(retrieve.router, prefix="/api/v1", tags=["Retrieval"])
app.include_router(rerank.router, prefix="/api/v1", tags=["Reranking"])
