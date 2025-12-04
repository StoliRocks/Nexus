"""
FastAPI application for Nexus Strands Agent Service.

Provides HTTP endpoints for strands-based agent execution:
- POST /api/v1/enrich - Control enrichment via multi-agent system
- POST /api/v1/enrich/batch - Batch control enrichment
- POST /api/v1/profile/generate - Framework profile generation
- POST /api/v1/reason - Single mapping reasoning
- POST /api/v1/reason/batch - Batch mapping reasoning
- POST /api/v1/reason/consolidated - Consolidated reasoning (single API call)
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nexus_strands_agent_service.app.config import get_settings
from nexus_strands_agent_service.app.routers import enrichment, reasoning

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Nexus Strands Agent Service API",
    version="1.0.0",
    description=(
        "ECS service for strands-based agent execution. "
        "Provides control enrichment (multi-agent system) and mapping reasoning generation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    logger.info(
        f"Starting {settings.service_name} in {settings.environment} environment"
    )
    logger.info(f"Bedrock model: {settings.bedrock_model_id}")
    logger.info(f"Reasoning model: {settings.reasoning_model_id}")
    logger.info("Service ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    logger.info("Shutting down service")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with execution time and request ID."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    # Skip logging for health checks to reduce noise
    if request.url.path not in ["/health", "/ready"]:
        logger.info(
            f"Request received: {request.method} {request.url.path} "
            f"[request_id={request_id}]"
        )

    try:
        response = await call_next(request)

        execution_time_ms = int((time.time() - start_time) * 1000)

        if request.url.path not in ["/health", "/ready"]:
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} time={execution_time_ms}ms "
                f"[request_id={request_id}]"
            )

        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"error={type(e).__name__}: {str(e)} time={execution_time_ms}ms "
            f"[request_id={request_id}]"
        )
        raise


@app.get("/health")
async def health_check():
    """
    Health check endpoint - returns service status.

    Always returns 200 to keep ALB target healthy.
    """
    return {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment,
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check - verifies service dependencies are available.

    Checks:
    - NexusEnrichmentAgent package is importable
    - NexusReasoningAgent package is importable
    """
    errors = []

    try:
        from nexus_enrichment_agent import ProfileDrivenMultiAgentProcessor  # noqa: F401
    except ImportError as e:
        errors.append(f"NexusEnrichmentAgent not available: {e}")

    try:
        from nexus_reasoning_agent import ReasoningGenerator  # noqa: F401
    except ImportError as e:
        errors.append(f"NexusReasoningAgent not available: {e}")

    if errors:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.service_name,
                "errors": errors,
            },
        )

    return {
        "status": "ready",
        "service": settings.service_name,
        "capabilities": ["enrichment", "reasoning", "profile_generation"],
    }


@app.get("/")
async def root():
    """Root endpoint - service information."""
    return {
        "service": "Nexus Strands Agent Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "endpoints": {
            "enrichment": {
                "enrich": "POST /api/v1/enrich",
                "batch": "POST /api/v1/enrich/batch",
                "profile": "POST /api/v1/profile/generate",
            },
            "reasoning": {
                "reason": "POST /api/v1/reason",
                "batch": "POST /api/v1/reason/batch",
                "consolidated": "POST /api/v1/reason/consolidated",
            },
        },
    }


# Include API routers
app.include_router(enrichment.router, prefix="/api/v1", tags=["Enrichment"])
app.include_router(reasoning.router, prefix="/api/v1", tags=["Reasoning"])
