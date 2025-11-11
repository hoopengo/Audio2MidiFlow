import logging
import sys
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from ..config import get_settings


def setup_logging() -> None:
    """Setup application logging configuration using loguru"""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Create logs directory if it doesn't exist
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Define log format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Simple format for console
    simple_format = "<level>{level: <8}</level> | <level>{message}</level>"

    # Add console handler
    logger.add(sys.stdout, format=simple_format, level="INFO", colorize=True)

    # Add file handler with rotation
    if settings.log_file:
        logger.add(
            settings.log_file,
            format=log_format,
            level=settings.log_level.upper(),
            rotation=f"{settings.log_max_bytes} B",
            retention=settings.log_backup_count,
            compression="zip",
            encoding="utf-8",
        )

    # Set specific logger levels for third-party libraries
    # Note: loguru doesn't directly control other loggers, but we can intercept them
    # by configuring the standard logging module to forward to loguru

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Configure specific loggers
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").handlers = [InterceptHandler()]
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )

    logger.info("Logging system initialized with loguru")


def get_logger(name: str):
    """Get a logger instance with the specified name"""
    # In loguru, we just return the main logger with context
    return logger.bind(name=name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""

    @property
    def logger(self):
        """Get logger for this class"""
        return logger.bind(
            class_name=self.__class__.__name__, module=self.__class__.__module__
        )


def log_function_call(func):
    """Decorator to log function calls"""

    def wrapper(*args, **kwargs):
        func_logger = logger.bind(function=func.__name__, module=func.__module__)
        func_logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            func_logger.error(f"{func.__name__} failed with error: {e}")
            raise

    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls"""

    async def wrapper(*args, **kwargs):
        func_logger = logger.bind(function=func.__name__, module=func.__module__)
        func_logger.debug(
            f"Calling async {func.__name__} with args={args}, kwargs={kwargs}"
        )

        try:
            result = await func(*args, **kwargs)
            func_logger.debug(f"async {func.__name__} completed successfully")
            return result
        except Exception as e:
            func_logger.error(f"async {func.__name__} failed with error: {e}")
            raise

    return wrapper


class ContextLogger:
    """Context manager for logging with context"""

    def __init__(self, context_logger, context: str, level: str = "INFO"):
        self.logger = context_logger
        self.context = context
        self.level = level

    def __enter__(self):
        self.logger.log(self.level, f"Starting: {self.context}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.log(self.level, f"Completed: {self.context}")
        else:
            self.logger.error(f"Failed: {self.context} - {exc_val}")
        return False  # Don't suppress exceptions


def log_performance(func):
    """Decorator to log function performance"""

    def wrapper(*args, **kwargs):
        func_logger = logger.bind(function=func.__name__, module=func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            func_logger.info(f"{func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            func_logger.error(
                f"{func.__name__} failed after {execution_time:.4f}s: {e}"
            )
            raise

    return wrapper


def log_async_performance(func):
    """Decorator to log async function performance"""

    async def wrapper(*args, **kwargs):
        func_logger = logger.bind(function=func.__name__, module=func.__module__)
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            func_logger.info(f"async {func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            func_logger.error(
                f"async {func.__name__} failed after {execution_time:.4f}s: {e}"
            )
            raise

    return wrapper


# Structured logging helpers
def log_structured(structured_logger, level: str, message: str, **kwargs):
    """Log structured data"""
    log_data = {"message": message, **kwargs}
    structured_logger.bind(**log_data).log(level, message)


def log_error_with_context(
    error_logger, error: Exception, context: Optional[dict] = None
):
    """Log error with additional context"""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }

    log_structured(error_logger, "ERROR", "Error occurred", **error_data)


def log_request_info(
    request_logger,
    method: str,
    path: str,
    status_code: int,
    processing_time: float,
    user_id: Optional[str] = None,
):
    """Log HTTP request information"""
    request_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "processing_time_ms": processing_time * 1000,
        "user_id": user_id,
    }

    log_structured(request_logger, "INFO", "HTTP request", **request_data)


def log_task_event(
    task_logger=None,
    task_id: str = "",
    event: str = "",
    status: str = "",
    details: Optional[dict] = None,
    **kwargs,
):
    """Log task-related events"""
    # Handle both task_logger and logger parameters for compatibility
    if task_logger is None and "logger" in kwargs:
        task_logger = kwargs.get("logger")

    task_data = {
        "task_id": task_id,
        "event": event,
        "status": status,
        "details": details or {},
    }

    log_structured(task_logger, "INFO", "Task event", **task_data)


class InterceptHandler(logging.Handler):
    """
    Default logging handler to intercept standard logging messages
    and forward them to loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )
