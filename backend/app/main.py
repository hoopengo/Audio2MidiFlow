import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .api.history import history_router
from .api.tasks import tasks_router
from .api.upload import upload_router
from .config import create_directories, get_settings
from .database import close_database_connections, init_database
from .utils.logging import setup_logging

# Setup logging
setup_logging()

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.version}")

    # Create necessary directories
    create_directories()

    # Initialize database with retry logic
    max_retries = 3
    retry_delay = 2  # seconds

    database_initialized = False
    for attempt in range(max_retries):
        if init_database():
            logger.info("Database initialized successfully")
            database_initialized = True
            break
        else:
            logger.warning(
                f"Database initialization failed (attempt {attempt + 1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

    if not database_initialized:
        logger.error("Failed to initialize database after multiple attempts")
        # Continue with limited functionality instead of crashing
        logger.warning(
            "Starting with limited functionality - database operations will fail"
        )

    logger.info("Application startup completed")

    yield

    # Shutdown
    logger.info("Shutting down application")
    close_database_connections()
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Convert MP3 audio recordings to MIDI format with asynchronous processing",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": str(exc) if settings.debug else None,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None,
            },
        },
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Improved validation error handler for 422 status codes"""
    logger.error(f"422 Error occurred for {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc)}")
    logger.error(f"Exception details: {exc}")

    # Check if it's a database connection issue
    if "database" in str(exc).lower() or "connection" in str(exc).lower():
        logger.error("Database connection issue detected")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_CONNECTION_ERROR",
                    "message": "Database connection error",
                    "details": "The application is unable to connect to database. Please try again later.",
                    "suggestion": "Contact support if the issue persists",
                },
            },
        )

    # Log request details for debugging
    logger.error(f"Request headers: {dict(request.headers)}")

    # Try to get request body for debugging
    try:
        body = await request.body()
        logger.error(f"Request body: {body}")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")

    if isinstance(exc, RequestValidationError):
        # Extract validation error details
        error_details = []
        for error in exc.errors():
            error_details.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input", "N/A"),
                }
            )

        logger.error(
            f"RequestValidationError for {request.method} {request.url.path}: {error_details}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": error_details,
                    "suggestion": "Please check your request format and try again",
                },
            },
        )

    # Fallback for other 422 errors
    logger.error(f"Unknown 422 error for {request.method} {request.url.path}: {exc}")
    logger.error(f"Exception repr: {repr(exc)}")
    if isinstance(exc, Exception):
        logger.error(f"Exception args: {exc.args}")
        import traceback

        logger.error(f"Exception traceback: {traceback.format_exc()}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "UNPROCESSABLE_ENTITY",
                "message": "The request could not be processed",
                "details": str(exc) if isinstance(exc, Exception) else None,
                "suggestion": "Please check your request format and try again",
            },
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    from .database import check_database_health

    db_health = await check_database_health()

    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "timestamp": "2024-01-01T12:00:00Z",  # Would use actual timestamp
        "version": settings.version,
        "database": db_health,
        "active_tasks": 0,  # Would get from task manager
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }


# Include API routers
app.include_router(upload_router, prefix="/api/v1", tags=["Upload"])
app.include_router(tasks_router, prefix="/api/v1", tags=["Tasks"])
app.include_router(history_router, prefix="/api/v1", tags=["History"])


# WebSocket endpoint for real-time updates (will be implemented later)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time task updates"""
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")

            # Echo back for now (will implement real updates later)
            await websocket.send_text(f"Echo: {data}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket connection closed")


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with processing time."""
    start_time = asyncio.get_event_loop().time()
    response = await call_next(request)
    process_time = asyncio.get_event_loop().time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Database health check middleware
@app.middleware("http")
async def check_database_health_middleware(request: Request, call_next):
    """
    Check database health before processing requests.

    Skips:
    - /health
    - /api/v1/tasks/statistics
    """
    if request.url.path in ("/health", "/api/v1/tasks/statistics"):
        return await call_next(request)

    try:
        from .database import check_database_health

        db_health = await check_database_health()
        if db_health.get("status") != "healthy":
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "DATABASE_UNAVAILABLE",
                        "message": "Database is currently unavailable",
                        "details": db_health,
                    },
                },
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Database connection error",
                    "details": str(e) if settings.debug else None,
                },
            },
        )

    return await call_next(request)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    return app


def run_server():
    """Run the FastAPI server"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True,
    )


if __name__ == "__main__":
    run_server()
