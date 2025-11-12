from enum import Enum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class OperationType(str, Enum):
    FILE_UPLOAD = "file_upload"
    AUDIO_LOADING = "audio_loading"
    FEATURE_EXTRACTION = "feature_extraction"
    PITCH_DETECTION = "pitch_detection"
    MIDI_GENERATION = "midi_generation"
    FILE_CLEANUP = "file_cleanup"
    ERROR_OCCURRED = "error_occurred"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"


class OperationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    INFO = "info"


class OperationHistory(Base):
    """Operation history model for audit trail"""

    __tablename__ = "operation_history"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Task reference
    task_id = Column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )

    # Operation details
    operation = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)

    # Timing information
    duration_ms = Column(Integer, nullable=True)  # Duration in milliseconds
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Additional metadata
    operation_metadata = Column(JSON, nullable=True)  # Flexible metadata storage

    # Relationships
    task = relationship("Task", backref="operations")

    # Indexes for performance
    __table_args__ = (
        Index("idx_history_task_timestamp", "task_id", "timestamp"),
        Index("idx_history_operation_timestamp", "operation", "timestamp"),
    )

    def __repr__(self):
        return f"<OperationHistory(task_id='{self.task_id}', operation='{self.operation}', status='{self.status}')>"

    @property
    def is_success(self) -> bool:
        """Check if operation was successful"""
        return self.status == OperationStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if operation failed"""
        return self.status == OperationStatus.FAILED

    @property
    def is_warning(self) -> bool:
        """Check if operation has warning status"""
        return self.status == OperationStatus.WARNING

    def to_dict(self) -> dict:
        """Convert operation history to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "operation": self.operation,
            "status": self.status,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "operation_metadata": self.operation_metadata,
        }

    @classmethod
    def create_operation(
        cls,
        task_id: str,
        operation: OperationType,
        status: OperationStatus,
        details: str = None,
        duration_ms: int = None,
        operation_metadata: dict = None,
    ) -> "OperationHistory":
        """Create a new operation history entry"""
        return cls(
            task_id=task_id,
            operation=operation.value,
            status=status.value,
            details=details,
            duration_ms=duration_ms,
            operation_metadata=operation_metadata,
        )

    @classmethod
    def log_success(
        cls,
        task_id: str,
        operation: OperationType,
        details: str = None,
        duration_ms: int = None,
        operation_metadata: dict = None,
    ) -> "OperationHistory":
        """Create a successful operation entry"""
        return cls.create_operation(
            task_id=task_id,
            operation=operation,
            status=OperationStatus.SUCCESS,
            details=details,
            duration_ms=duration_ms,
            operation_metadata=operation_metadata,
        )

    @classmethod
    def log_error(
        cls,
        task_id: str,
        operation: OperationType,
        details: str = None,
        duration_ms: int = None,
        operation_metadata: dict = None,
    ) -> "OperationHistory":
        """Create an error operation entry"""
        return cls.create_operation(
            task_id=task_id,
            operation=operation,
            status=OperationStatus.FAILED,
            details=details,
            duration_ms=duration_ms,
            operation_metadata=operation_metadata,
        )

    @classmethod
    def log_warning(
        cls,
        task_id: str,
        operation: OperationType,
        details: str = None,
        duration_ms: int = None,
        operation_metadata: dict = None,
    ) -> "OperationHistory":
        """Create a warning operation entry"""
        return cls.create_operation(
            task_id=task_id,
            operation=operation,
            status=OperationStatus.WARNING,
            details=details,
            duration_ms=duration_ms,
            operation_metadata=operation_metadata,
        )

    @classmethod
    def log_info(
        cls,
        task_id: str,
        operation: OperationType,
        details: str = None,
        duration_ms: int = None,
        operation_metadata: dict = None,
    ) -> "OperationHistory":
        """Create an info operation entry"""
        return cls.create_operation(
            task_id=task_id,
            operation=operation,
            status=OperationStatus.INFO,
            details=details,
            duration_ms=duration_ms,
            operation_metadata=operation_metadata,
        )
