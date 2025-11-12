import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from .base import Base


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(str, Enum):
    QUEUED = "queued"
    AUDIO_LOADING = "audio_loading"
    FEATURE_EXTRACTION = "feature_extraction"
    PITCH_DETECTION = "pitch_detection"
    MIDI_GENERATION = "midi_generation"
    FINALIZATION = "finalization"


class Task(Base):
    """Task model for tracking audio to MIDI conversion jobs"""

    __tablename__ = "tasks"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Task identifier
    task_id = Column(String(36), unique=True, nullable=False, index=True)

    # File information
    original_filename = Column(String(255), nullable=False)
    input_file_path = Column(String(500), nullable=False)
    output_file_path = Column(String(500), nullable=True)

    # Status tracking
    status = Column(String(50), nullable=False, default=TaskStatus.PENDING, index=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    processing_stage = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # File sizes
    file_size = Column(BigInteger, nullable=True)
    output_size = Column(BigInteger, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)

    # Processing metrics
    processing_time = Column(Integer, nullable=True)  # in seconds

    # Indexes for performance
    __table_args__ = (
        Index("idx_task_status", "status", "created_at"),
        Index("idx_task_created", "created_at"),
    )

    def __repr__(self):
        return f"<Task(task_id='{self.task_id}', status='{self.status}', progress={self.progress}%)>"

    @property
    def is_completed(self) -> bool:
        """Check if task is completed successfully"""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == TaskStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Check if task is currently processing"""
        return self.status == TaskStatus.PROCESSING

    @property
    def can_be_cancelled(self) -> bool:
        """Check if task can be cancelled"""
        return self.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]

    def to_dict(self) -> dict:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "original_filename": self.original_filename,
            "status": self.status,
            "progress": self.progress,
            "processing_stage": self.processing_stage,
            "error_message": self.error_message,
            "file_size": self.file_size,
            "output_size": self.output_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "estimated_completion": self.estimated_completion.isoformat()
            if self.estimated_completion
            else None,
            "processing_time": self.processing_time,
        }

    @classmethod
    def create_new(
        cls, filename: str, input_path: str, file_size: int = None
    ) -> "Task":
        """Create a new task instance"""
        return cls(
            task_id=str(uuid.uuid4()),
            original_filename=filename,
            input_file_path=input_path,
            file_size=file_size,
            status=TaskStatus.PENDING,
            progress=0,
        )

    def update_progress(self, progress: int, stage: ProcessingStage = None):
        """Update task progress"""
        self.progress = max(0, min(100, progress))
        if stage:
            self.processing_stage = stage.value

    def mark_started(self):
        """Mark task as started"""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.processing_stage = ProcessingStage.QUEUED.value

    def mark_completed(self, output_path: str, output_size: int = None):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.output_file_path = output_path
        self.output_size = output_size
        self.progress = 100
        self.processing_stage = None

        # Calculate processing time
        if self.started_at:
            self.processing_time = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def mark_failed(self, error_message: str):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.processing_stage = None

        # Calculate processing time
        if self.started_at:
            self.processing_time = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def mark_cancelled(self):
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.processing_stage = None
