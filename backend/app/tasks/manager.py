import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set

from loguru import logger
from sqlalchemy import select, update

from ..database import get_async_db
from ..models import (
    OperationHistory,
    OperationType,
    ProcessingStage,
    Task,
    TaskStatus,
)
from ..utils import get_file_handler
from ..utils.logging import log_task_event
from .processor import AudioProcessor


class TaskManager:
    """Manager for handling background task processing"""

    def __init__(self):
        self.file_handler = get_file_handler()
        self.audio_processor = AudioProcessor()
        self._active_tasks: Set[str] = set()
        self._task_locks: Dict[str, asyncio.Lock] = {}
        self._max_concurrent_tasks = 3  # Will be configurable

    async def get_task_lock(self, task_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific task"""
        if task_id not in self._task_locks:
            self._task_locks[task_id] = asyncio.Lock()
        return self._task_locks[task_id]

    async def process_task(self, task_id: str) -> bool:
        """
        Process a single task

        Args:
            task_id: ID of the task to process

        Returns:
            True if processing was successful
        """
        # Get task lock to prevent concurrent processing
        task_lock = await self.get_task_lock(task_id)

        async with task_lock:
            # Check if task is already being processed
            if task_id in self._active_tasks:
                logger.warning(f"Task {task_id} is already being processed")
                return False

            # Check concurrent task limit
            if len(self._active_tasks) >= self._max_concurrent_tasks:
                logger.info(f"Concurrent task limit reached, queuing task {task_id}")
                await self._queue_task(task_id)
                return True

            try:
                # Add to active tasks
                self._active_tasks.add(task_id)

                # Get task from database
                async with get_async_db() as db:
                    result = await db.execute(
                        select(Task).where(Task.task_id == task_id)
                    )
                    task = result.scalar_one_or_none()

                    if not task:
                        logger.error(f"Task {task_id} not found")
                        return False

                    # Check if task can be processed
                    if task.status not in [TaskStatus.PENDING, TaskStatus.FAILED]:
                        logger.warning(
                            f"Task {task_id} cannot be processed (status: {task.status})"
                        )
                        return False

                    # Mark task as started
                    task.mark_started()
                    await db.commit()

                    # Log task start
                    operation = OperationHistory.log_info(
                        task_id=task_id,
                        operation=OperationType.TASK_STARTED,
                        details=f"Task processing started: {task.original_filename}",
                    )
                    db.add(operation)
                    await db.commit()

                # Log task event
                log_task_event(
                    task_logger=logger,
                    task_id=task_id,
                    event="processing_started",
                    status="processing",
                    details={"filename": task.original_filename},
                )

                # Process the task
                success = await self._execute_task_processing(task_id)

                # Remove from active tasks
                self._active_tasks.discard(task_id)

                return success

            except Exception as e:
                logger.error(f"Failed to process task {task_id}: {e}", exc_info=True)

                # Remove from active tasks
                self._active_tasks.discard(task_id)

                # Mark task as failed
                await self._mark_task_failed(task_id, str(e))

                return False

    async def _execute_task_processing(self, task_id: str) -> bool:
        """
        Execute the actual task processing

        Args:
            task_id: ID of the task to process

        Returns:
            True if processing was successful
        """
        try:
            # Get task details
            async with get_async_db() as db:
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                task = result.scalar_one()

            # Update progress through processing stages
            await self._update_task_progress(task_id, 10, ProcessingStage.AUDIO_LOADING)

            # Load and validate audio file
            audio_data = await self.audio_processor.load_audio(task.input_file_path)
            await self._update_task_progress(
                task_id, 25, ProcessingStage.FEATURE_EXTRACTION
            )

            # Extract audio features
            features = await self.audio_processor.extract_features(audio_data)
            await self._update_task_progress(
                task_id, 50, ProcessingStage.PITCH_DETECTION
            )

            # Detect pitches and create notes
            notes = await self.audio_processor.detect_pitches(audio_data, features)
            await self._update_task_progress(
                task_id, 75, ProcessingStage.MIDI_GENERATION
            )

            # Generate MIDI file
            midi_content = await self.audio_processor.generate_midi(notes, features)
            await self._update_task_progress(task_id, 90, ProcessingStage.FINALIZATION)

            # Save MIDI file
            output_path = await self.file_handler.save_output_file(
                file_content=midi_content, task_id=task_id, extension=".mid"
            )

            # Mark task as completed
            await self._mark_task_completed(task_id, output_path, len(midi_content))

            logger.info(f"Task {task_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Task processing failed for {task_id}: {e}", exc_info=True)
            await self._mark_task_failed(task_id, str(e))
            return False

    async def _update_task_progress(
        self, task_id: str, progress: int, stage: ProcessingStage
    ) -> None:
        """
        Update task progress in database

        Args:
            task_id: ID of the task
            progress: Progress percentage (0-100)
            stage: Current processing stage
        """
        try:
            async with get_async_db() as db:
                await db.execute(
                    update(Task)
                    .where(Task.task_id == task_id)
                    .values(progress=progress, processing_stage=stage.value)
                )
                await db.commit()

            # Log progress update
            log_task_event(
                task_logger=logger,
                task_id=task_id,
                event="progress_update",
                status="processing",
                details={"progress": progress, "stage": stage.value},
            )

        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")

    async def _mark_task_completed(
        self, task_id: str, output_path: str, output_size: int
    ) -> None:
        """
        Mark task as completed in database

        Args:
            task_id: ID of the task
            output_path: Path to generated MIDI file
            output_size: Size of output file in bytes
        """
        try:
            async with get_async_db() as db:
                # Update task
                await db.execute(
                    update(Task)
                    .where(Task.task_id == task_id)
                    .values(
                        status=TaskStatus.COMPLETED,
                        progress=100,
                        processing_stage=None,
                        output_file_path=output_path,
                        output_size=output_size,
                        completed_at=datetime.utcnow(),
                    )
                )
                await db.commit()

                # Log completion
                operation = OperationHistory.log_success(
                    task_id=task_id,
                    operation=OperationType.TASK_COMPLETED,
                    details=f"Task completed successfully. Output: {output_path}",
                    operation_metadata={
                        "output_path": output_path,
                        "output_size": output_size,
                    },
                )
                db.add(operation)
                await db.commit()

            # Log task event
            log_task_event(
                task_logger=logger,
                task_id=task_id,
                event="processing_completed",
                status="completed",
                details={"output_path": output_path, "output_size": output_size},
            )

        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as completed: {e}")

    async def _mark_task_failed(self, task_id: str, error_message: str) -> None:
        """
        Mark task as failed in database

        Args:
            task_id: ID of the task
            error_message: Error description
        """
        try:
            async with get_async_db() as db:
                # Update task
                await db.execute(
                    update(Task)
                    .where(Task.task_id == task_id)
                    .values(
                        status=TaskStatus.FAILED,
                        processing_stage=None,
                        error_message=error_message,
                        completed_at=datetime.utcnow(),
                    )
                )
                await db.commit()

                # Log failure
                operation = OperationHistory.log_error(
                    task_id=task_id,
                    operation=OperationType.TASK_FAILED,
                    details=f"Task failed: {error_message}",
                    operation_metadata={"error_message": error_message},
                )
                db.add(operation)
                await db.commit()

            # Log task event
            log_task_event(
                task_logger=logger,
                task_id=task_id,
                event="processing_failed",
                status="failed",
                details={"error_message": error_message},
            )

        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as failed: {e}")

    async def _queue_task(self, task_id: str) -> None:
        """
        Queue a task for later processing

        Args:
            task_id: ID of the task to queue
        """
        # For now, just log the queuing
        # In a full implementation, this would use a proper queue system
        logger.info(f"Task {task_id} queued for later processing")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if cancellation was successful
        """
        try:
            async with get_async_db() as db:
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                task = result.scalar_one_or_none()

                if not task:
                    logger.error(f"Task {task_id} not found for cancellation")
                    return False

                if not task.can_be_cancelled:
                    logger.warning(
                        f"Task {task_id} cannot be cancelled (status: {task.status})"
                    )
                    return False

                # Mark task as cancelled
                task.mark_cancelled()
                await db.commit()

                # Log cancellation
                operation = OperationHistory.log_info(
                    task_id=task_id,
                    operation=OperationType.TASK_CANCELLED,
                    details="Task cancelled by user request",
                )
                db.add(operation)
                await db.commit()

            # Remove from active tasks if it's there
            self._active_tasks.discard(task_id)

            # Log task event
            log_task_event(
                task_logger=logger,
                task_id=task_id,
                event="task_cancelled",
                status="cancelled",
                details={},
            )

            logger.info(f"Task {task_id} cancelled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def get_active_tasks_count(self) -> int:
        """
        Get count of currently active tasks

        Returns:
            Number of active tasks
        """
        return len(self._active_tasks)

    async def cleanup_old_tasks(self, hours: int = 24) -> int:
        """
        Clean up old completed tasks

        Args:
            hours: Age in hours for tasks to clean up

        Returns:
            Number of tasks cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cleaned_count = 0

            async with get_async_db() as db:
                # Find old completed/failed tasks
                result = await db.execute(
                    select(Task).where(
                        (Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]))
                        & (Task.created_at < cutoff_time)
                    )
                )
                old_tasks = result.scalars().all()

                for task in old_tasks:
                    # Delete associated files
                    if task.input_file_path:
                        await self.file_handler.delete_file(task.input_file_path)
                    if task.output_file_path:
                        await self.file_handler.delete_file(task.output_file_path)

                    # Delete task from database
                    await db.delete(task)
                    cleaned_count += 1

                await db.commit()

            logger.info(f"Cleaned up {cleaned_count} old tasks")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

    async def get_task_statistics(self) -> dict:
        """
        Get task processing statistics

        Returns:
            Dictionary with task statistics
        """
        try:
            async with get_async_db() as db:
                # Count tasks by status
                stats = {}
                for status in TaskStatus:
                    # Use count() instead of loading all records
                    result = await db.execute(
                        select(Task).where(Task.status == status.value)
                    )
                    count = len(result.scalars().all())
                    stats[status.value] = count

                # Add active tasks count
                stats["active_processing"] = await self.get_active_tasks_count()

                return stats

        except Exception as e:
            logger.error(f"Failed to get task statistics: {e}", exc_info=True)
            return {}


# Global task manager instance
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """Get global task manager instance"""
    return task_manager
