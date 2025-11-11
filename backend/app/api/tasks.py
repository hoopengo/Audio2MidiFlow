from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select

from ..database import check_database_health, get_async_db
from ..models import Task, TaskStatus
from ..tasks.manager import get_task_manager
from ..utils import get_file_handler, validate_pagination_params, validate_task_id

tasks_router = APIRouter()


class TaskResponse(BaseModel):
    """Response model for task information"""

    success: bool = True
    data: dict


class TaskListResponse(BaseModel):
    """Response model for task list"""

    success: bool = True
    data: dict


class PaginationInfo(BaseModel):
    """Pagination information"""

    total: int
    limit: int
    offset: int
    has_more: bool


@tasks_router.get("/tasks/statistics", response_model=TaskResponse, tags=["Tasks"])
async def get_task_statistics():
    """
    Get task processing statistics

    Returns:
        Task statistics and metrics
    """
    try:
        # Check database connection first
        db_health = await check_database_health()
        if db_health["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "DATABASE_UNAVAILABLE",
                    "message": "Database is currently unavailable",
                    "details": db_health,
                },
            )

        task_manager = get_task_manager()
        stats = await task_manager.get_task_statistics()

        # Add additional metrics
        async with get_async_db() as db:
            try:
                # Get total tasks
                total_result = await db.execute(select(Task))
                total_tasks = len(total_result.scalars().all())

                # Get recent tasks (last 24 hours)
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_result = await db.execute(
                    select(Task).where(Task.created_at >= recent_cutoff)
                )
                recent_tasks = len(recent_result.scalars().all())

                stats.update(
                    {
                        "total_tasks": total_tasks,
                        "recent_tasks_24h": recent_tasks,
                        "active_processing": await task_manager.get_active_tasks_count(),
                    }
                )
            except Exception as db_error:
                logger.error(f"Database error in statistics: {db_error}", exc_info=True)
                # Return basic stats even if detailed queries fail
                stats.update(
                    {
                        "total_tasks": 0,
                        "recent_tasks_24h": 0,
                        "active_processing": await task_manager.get_active_tasks_count(),
                    }
                )

        return TaskResponse(
            data=stats, message="Task statistics retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "STATISTICS_FAILED",
                "message": "Failed to retrieve task statistics",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@tasks_router.get("/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of tasks to return"
    ),
    offset: Optional[int] = Query(None, ge=0, description="Number of tasks to skip"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    sort: Optional[str] = Query("created_at", description="Sort field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
):
    """
    List tasks with pagination and filtering

    Args:
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip
        status: Filter by task status
        sort: Field to sort by
        order: Sort order (asc/desc)

    Returns:
        Paginated list of tasks
    """
    try:
        # Check database connection first
        db_health = await check_database_health()
        if db_health["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "DATABASE_UNAVAILABLE",
                    "message": "Database is currently unavailable",
                    "details": db_health,
                },
            )

        # Validate pagination parameters
        validated_limit, validated_offset = validate_pagination_params(limit, offset)

        async with get_async_db() as db:
            # Build query
            query = select(Task)

            # Apply status filter
            if status:
                try:
                    status_enum = TaskStatus(status)
                    query = query.where(Task.status == status_enum)
                except ValueError:
                    logger.warning(f"Invalid status filter: {status}")

            # Apply sorting
            if sort in [
                "created_at",
                "started_at",
                "completed_at",
                "progress",
                "status",
            ]:
                sort_column = getattr(Task, sort)
                if order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            else:
                # Default sorting
                query = query.order_by(Task.created_at.desc())

            # Get total count
            count_query = select(Task).where(Task.task_id.isnot(None))
            if status:
                try:
                    status_enum = TaskStatus(status)
                    count_query = count_query.where(Task.status == status_enum)
                except ValueError:
                    pass
            total_result = await db.execute(count_query)
            total = len(total_result.scalars().all())

            # Apply pagination
            query = query.offset(validated_offset).limit(validated_limit)
            result = await db.execute(query)
            tasks = result.scalars().all()

            # Convert to response format
            task_list = []
            for task in tasks:
                task_data = task.to_dict()
                # Add download URL for completed tasks
                if task.status == TaskStatus.COMPLETED and task.output_file_path:
                    task_data["download_url"] = f"/api/v1/tasks/{task.task_id}/download"
                task_list.append(task_data)

            # Calculate pagination info
            has_more = validated_offset + validated_limit < total

            return TaskListResponse(
                data={
                    "tasks": task_list,
                    "pagination": {
                        "total": total,
                        "limit": validated_limit,
                        "offset": validated_offset,
                        "has_more": has_more,
                    },
                },
                message=f"Retrieved {len(task_list)} tasks",
            )

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TASK_LIST_FAILED",
                "message": "Failed to retrieve task list",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@tasks_router.delete("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def cancel_task(
    task_id: str = Path(..., description="Task ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Cancel a task

    Args:
        task_id: UUID of the task to cancel

    Returns:
        Cancellation result

    Raises:
        HTTPException: If task is not found or cannot be cancelled
    """
    try:
        # Validate task ID
        validate_task_id(task_id)

        # Get task manager
        task_manager = get_task_manager()

        # Cancel the task
        success = await task_manager.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "TASK_CANCELLATION_FAILED",
                    "message": "Task cannot be cancelled",
                    "details": {"task_id": task_id},
                },
            )

        return TaskResponse(
            data={
                "task_id": task_id,
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
            },
            message="Task cancelled successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CANCELLATION_FAILED",
                "message": "Failed to cancel task",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@tasks_router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task_status(task_id: str = Path(..., description="Task ID")):
    """
    Get detailed status of a specific task

    Args:
        task_id: UUID of the task

    Returns:
        Detailed task information

    Raises:
        HTTPException: If task is not found
    """
    try:
        # Validate task ID
        validate_task_id(task_id)

        async with get_async_db() as db:
            result = await db.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "TASK_NOT_FOUND",
                        "message": "Task not found",
                        "details": {"task_id": task_id},
                    },
                )

            # Prepare response data
            task_data = task.to_dict()

            # Add download URL if completed
            if task.status == TaskStatus.COMPLETED and task.output_file_path:
                task_data["download_url"] = f"/api/v1/tasks/{task_id}/download"

            # Add estimated completion time if processing
            if task.status == TaskStatus.PROCESSING and task.progress > 0:
                # Simple estimation based on current progress
                if task.started_at:
                    elapsed = (datetime.utcnow() - task.started_at).total_seconds()
                    if task.progress > 0:
                        estimated_total = elapsed * 100 / task.progress
                        remaining = estimated_total - elapsed
                        estimated_completion = datetime.utcnow() + timedelta(
                            seconds=remaining
                        )
                        task_data["estimated_completion"] = (
                            estimated_completion.isoformat()
                        )

            return TaskResponse(
                data=task_data, message="Task status retrieved successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "STATUS_RETRIEVAL_FAILED",
                "message": "Failed to retrieve task status",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@tasks_router.get("/tasks/{task_id}/download", tags=["Tasks"])
async def download_midi_file(task_id: str = Path(..., description="Task ID")):
    """
    Download generated MIDI file

    Args:
        task_id: UUID of the task

    Returns:
        MIDI file as download

    Raises:
        HTTPException: If task is not found or not completed
    """
    try:
        # Validate task ID
        validate_task_id(task_id)

        async with get_async_db() as db:
            result = await db.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "TASK_NOT_FOUND",
                        "message": "Task not found",
                        "details": {"task_id": task_id},
                    },
                )

            if task.status != TaskStatus.COMPLETED:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "TASK_NOT_COMPLETED",
                        "message": "MIDI file not available for download",
                        "details": {"task_id": task_id, "current_status": task.status},
                    },
                )

            if not task.output_file_path:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "OUTPUT_FILE_NOT_FOUND",
                        "message": "Output file not found",
                        "details": {"task_id": task_id},
                    },
                )

            # Check if file exists
            file_handler = get_file_handler()
            if not file_handler.file_exists(task.output_file_path):
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "OUTPUT_FILE_MISSING",
                        "message": "Output file is missing",
                        "details": {"output_path": task.output_file_path},
                    },
                )

            # Generate filename
            original_name = task.original_filename
            base_name = (
                original_name.rsplit(".", 1)[0]
                if "." in original_name
                else original_name
            )
            midi_filename = f"{base_name}.mid"

            # Return file
            return FileResponse(
                path=task.output_file_path,
                filename=midi_filename,
                media_type="audio/midi",
                headers={
                    "Content-Disposition": f"attachment; filename={midi_filename}"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download MIDI for task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DOWNLOAD_FAILED",
                "message": "Failed to download MIDI file",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@tasks_router.post("/tasks/cleanup", response_model=TaskResponse, tags=["Tasks"])
async def cleanup_old_tasks(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    hours: int = Query(24, ge=1, le=168, description="Age in hours for cleanup"),
):
    """
    Clean up old completed and failed tasks

    Args:
        hours: Age threshold for cleanup (1-168 hours)

    Returns:
        Cleanup operation results
    """
    try:
        task_manager = get_task_manager()

        # Run cleanup in background
        background_tasks.add_task(task_manager.cleanup_old_tasks, hours)

        return TaskResponse(
            data={
                "cleanup_initiated": True,
                "hours_threshold": hours,
                "timestamp": datetime.utcnow().isoformat(),
            },
            message=f"Cleanup initiated for tasks older than {hours} hours",
        )

    except Exception as e:
        logger.error(f"Failed to initiate cleanup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CLEANUP_INITIATION_FAILED",
                "message": "Failed to initiate cleanup",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )
