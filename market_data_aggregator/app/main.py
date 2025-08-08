"""
Main FastAPI application for Market Data Aggregator Service.
Includes lifespan management for background tasks and service initialization.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time

from app.core.config import settings
from app.core.logging_config import setup_logging, create_logger
from app.api.endpoints import router as api_router
from app.services.data_aggregator import aggregator_service
from app.services.cache import cache_service
from app.api.schemas import ErrorResponse

# Setup logging first
setup_logging()
logger = create_logger(__name__)

# Global startup time
startup_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown of background services.
    """
    # Startup
    logger.info("Starting Market Data Aggregator Service", extra={
        "version": settings.app_version,
        "debug": settings.debug
    })
    
    try:
        # Initialize data aggregator service
        await aggregator_service.initialize()
        
        # Start background tasks
        await aggregator_service.start_background_tasks()
        
        logger.info("Market Data Aggregator Service started successfully")
        
        # Store startup time globally
        global startup_time
        startup_time = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to start Market Data Aggregator Service", extra={
            "error": str(e)
        })
        raise
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down Market Data Aggregator Service")
    
    try:
        # Shutdown aggregator service
        await aggregator_service.shutdown()
        
        logger.info("Market Data Aggregator Service shutdown completed")
        
    except Exception as e:
        logger.error("Error during service shutdown", extra={
            "error": str(e)
        })


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="High-performance market data aggregation service with circuit breaker resilience",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]  # Configure as needed
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    start_time = time.time()
    
    # Log request
    logger.info("Request received", extra={
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    })
    
    try:
        response = await call_next(request)
        
        # Calculate request duration
        process_time = time.time() - start_time
        
        # Log response
        logger.info("Request completed", extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "client_ip": request.client.host if request.client else None
        })
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # Calculate request duration for error cases
        process_time = time.time() - start_time
        
        # Log error
        logger.error("Request failed", extra={
            "method": request.method,
            "url": str(request.url),
            "error": str(e),
            "process_time": round(process_time, 4),
            "client_ip": request.client.host if request.client else None
        })
        
        # Return structured error response
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                error_code="INTERNAL_ERROR"
            ).dict()
        )


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with structured response."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Endpoint not found",
            error_code="NOT_FOUND",
            details={
                "path": request.url.path,
                "method": request.method
            }
        ).dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors with structured response."""
    logger.error("Internal server error", extra={
        "path": request.url.path,
        "method": request.method,
        "error": str(exc)
    })
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR"
        ).dict()
    )


# Include API routes
app.include_router(api_router, tags=["Market Data API"])


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs" if settings.debug else "disabled",
        "timestamp": datetime.utcnow()
    }


# Alternative health check endpoint (for load balancers)
@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Simple health check endpoint for load balancers."""
    try:
        # Quick Redis health check
        redis_healthy = await cache_service.health_check()
        
        # Check if background tasks are running
        tasks_running = aggregator_service.are_background_tasks_running()
        
        if redis_healthy and tasks_running:
            return {"status": "healthy"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "redis": redis_healthy, "tasks": tasks_running}
            )
            
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


# Readiness check endpoint (for Kubernetes)
@app.get("/ready", include_in_schema=False)
async def ready():
    """Readiness check endpoint for Kubernetes deployments."""
    try:
        # Check if service is fully initialized
        redis_healthy = await cache_service.health_check()
        tasks_running = aggregator_service.are_background_tasks_running()
        
        # Get last update times to ensure data is being fetched
        last_updates = aggregator_service.get_last_update_times()
        has_recent_updates = any(
            update and (datetime.utcnow() - update).total_seconds() < 3600  # Within last hour
            for update in last_updates.values()
        )
        
        if redis_healthy and tasks_running and has_recent_updates:
            return {"status": "ready"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "redis": redis_healthy,
                    "tasks": tasks_running,
                    "recent_updates": has_recent_updates
                }
            )
            
    except Exception as e:
        logger.error("Readiness check failed", extra={"error": str(e)})
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )


# Application information endpoint
@app.get("/info", include_in_schema=False)
async def info():
    """Get detailed application information."""
    try:
        uptime_seconds = (datetime.utcnow() - startup_time).total_seconds()
        
        # Get provider status
        provider_health = await aggregator_service.get_provider_health_status()
        circuit_status = await aggregator_service.get_circuit_breaker_status()
        
        # Get last update times
        last_updates = aggregator_service.get_last_update_times()
        
        return {
            "service": {
                "name": settings.app_name,
                "version": settings.app_version,
                "debug": settings.debug,
                "uptime_seconds": uptime_seconds,
                "startup_time": startup_time
            },
            "providers": {
                "health": provider_health,
                "circuits": circuit_status
            },
            "background_tasks": {
                "running": aggregator_service.are_background_tasks_running(),
                "last_updates": last_updates
            },
            "cache": {
                "redis_connected": await cache_service.health_check(),
                "quotes_ttl": settings.quotes_cache_ttl,
                "assets_ttl": settings.assets_cache_ttl
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Failed to get application info", extra={"error": str(e)})
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )