"""
Main FastAPI application for Luxury Item Appraisal Agent.
Integrates Trend Analysis, Pricing Estimation, and Agent Orchestration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers import trends, pricing, agent, image
# Import configuration and logging
from config.settings import settings
from config.logging import setup_logging

# Set up logging
logger = setup_logging()

app = FastAPI(
    title="Luxury Item Appraisal Agent API",
    description="API using an LLM agent to generate appraisal reports by calling internal tools for pricing and trend analysis.",
    version="2.0.0", # Updated version
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(pricing.router, prefix="/tools", tags=["Internal Tools"])
app.include_router(trends.router, prefix="/tools", tags=["Internal Tools"])
app.include_router(image.router, prefix="/tools/image", tags=["Image Analysis"])

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing basic API information and links to docs."""
    return {
        "name": "Luxury Item Appraisal Agent API",
        "version": app.version,
        "description": app.description,
        "environment": settings.environment,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "agent_endpoint": "/agent/appraise",
        "tool_endpoints": [
            "/tools/price/basic",
            "/tools/price/advanced",
            "/tools/trends/search",
            "/tools/trends/social",
            "/tools/trends/news",
            "/tools/trends/resale",
            "/tools/image/analyze",
            "/tools/image/compare"
        ]
    }

# Note: The old /analyze endpoint is removed as its functionality is now
# split across the /tools/trends/* endpoints and orchestrated by the agent.
# The if __name__ == "__main__" block is removed as the app is run via run.py 