import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import wraps
from typing import Generator

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings
from .models import Base, Task


def retry_database_operation(max_retries=3, delay=1):
    """Decorator to retry database operations"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "database" in str(e).lower() or "connection" in str(e).lower():
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Database operation failed, retrying (attempt {attempt + 1}/{max_retries}): {e}"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"Database operation failed after {max_retries} attempts: {e}"
                            )
                            raise HTTPException(
                                status_code=503,
                                detail={
                                    "error": "DATABASE_UNAVAILABLE",
                                    "message": "Database is currently unavailable",
                                    "details": "Please try again later",
                                },
                            )
                    else:
                        raise

        return wrapper

    return decorator


# Global variables for database connections
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None


def get_database_url() -> str:
    """Get database URL from settings"""
    settings = get_settings()
    return settings.database_url


def create_sync_engine():
    """Create synchronous SQLAlchemy engine"""
    global engine
    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,  # SQLite specific
            "timeout": 20,
        },
        poolclass=StaticPool,
        echo=settings.debug,  # Log SQL queries in debug mode
        pool_pre_ping=True,
    )

    logger.info(f"Created synchronous database engine: {settings.database_url}")
    return engine


def create_async_database_engine():
    """Create asynchronous SQLAlchemy engine"""
    global async_engine
    settings = get_settings()

    # Convert SQLite URL to async format
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    async_engine = create_async_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 20},
        pool_pre_ping=True,
        echo=settings.debug,
    )

    logger.info(f"Created asynchronous database engine: {db_url}")
    return async_engine


def create_session_factory():
    """Create session factory for synchronous operations"""
    global SessionLocal
    if engine is None:
        create_sync_engine()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    logger.info("Created synchronous session factory")
    return SessionLocal


def create_async_session_factory():
    """Create session factory for asynchronous operations"""
    global AsyncSessionLocal
    if async_engine is None:
        create_async_database_engine()

    AsyncSessionLocal = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Created asynchronous session factory")
    return AsyncSessionLocal


def init_database():
    """Initialize database with all tables"""
    try:
        # Create synchronous engine and tables
        sync_engine = create_sync_engine()
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")

        # Create session factories
        create_session_factory()
        create_async_session_factory()

        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def get_db() -> Generator[Session, None, None]:
    """Get database session for synchronous operations"""
    if SessionLocal is None:
        create_session_factory()

    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db():
    """Get database session for asynchronous operations"""
    if AsyncSessionLocal is None:
        create_async_session_factory()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


def close_database_connections():
    """Close all database connections"""
    global engine, async_engine

    if engine:
        engine.dispose()
        logger.info("Closed synchronous database engine")

    if async_engine:
        async_engine.sync_engine.dispose()
        logger.info("Closed asynchronous database engine")


class DatabaseManager:
    """Database manager class for handling operations"""

    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None

    def initialize(self):
        """Initialize database manager"""
        self.engine = create_sync_engine()
        self.async_engine = create_async_database_engine()
        self.session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.async_session_factory = async_sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database manager initialized successfully")

    def get_session(self) -> Session:
        """Get synchronous database session"""
        return self.session_factory()

    async def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session"""
        return self.async_session_factory()

    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            self.async_engine.sync_engine.dispose()
        logger.info("Database manager connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    return db_manager


# Database health check
async def check_database_health() -> dict:
    """Check database health and connectivity"""
    try:
        async with get_async_db() as session:
            # Simple query to test connectivity
            await session.execute(text("SELECT 1"))
            await session.commit()

            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        }


# Database cleanup utilities
async def cleanup_old_tasks(hours: int = 24):
    """Clean up old tasks and their files"""

    try:
        async with get_async_db() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Find old tasks
            old_tasks = (
                await session.query(Task).filter(Task.created_at < cutoff_time).all()
            )

            cleaned_count = 0
            for task in old_tasks:
                # Delete associated files
                await task.delete_files()
                # Delete task from database
                await session.delete(task)
                cleaned_count += 1

            await session.commit()
            logger.info(f"Cleaned up {cleaned_count} old tasks")

            return cleaned_count
    except Exception as e:
        logger.error(f"Failed to cleanup old tasks: {e}")
        return 0
