"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from phoenix.otel import register
from openinference.instrumentation.anthropic import AnthropicInstrumentor

from src.config.settings import settings
from src.config.logging_config import setup_logging, get_logger
from src.api.routes import health, ingest, query, upload

# Setup logging
setup_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Phoenix tracing setup
# Registers an OpenTelemetry tracer that exports spans to the Phoenix
# instance running at localhost:6006. Every Anthropic API call is
# automatically instrumented -- you'll see triage, generation, and
# small-talk LLM calls as individual spans in the Phoenix UI.
# ---------------------------------------------------------------------------
try:
    tracer_provider = register(
        project_name="vedamax-sentimedic",
        endpoint="http://localhost:6006/v1/traces",
    )
    AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("Phoenix tracing enabled at http://localhost:6006")
except Exception as exc:
    logger.warning(f"Phoenix tracing could not be enabled: {exc} -- continuing without tracing")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal health management with sentiment-aware agentic RAG",
    debug=settings.DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(upload.router)
app.include_router(ingest.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to SentiMedical-RAG API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )