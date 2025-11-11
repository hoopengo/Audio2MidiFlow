from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from ..database import get_async_db
from ..models import OperationHistory, Task
from ..utils import validate_pagination_params

history_router = APIRouter()


class HistoryResponse(BaseModel):
    """Response model for operation history"""

    success: bool = True
    data: dict


class HistoryListResponse(BaseModel):
    """Response model for history list"""

    success: bool = True
    data: dict


class HistoryStatsResponse(BaseModel):
    """Response model for history statistics"""

    success: bool = True
    data: dict


@history_router.get("/history", response_model=HistoryListResponse, tags=["History"])
async def get_operation_history(
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of records to return"
    ),
    offset: Optional[int] = Query(None, ge=0, description="Number of records to skip"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by operation status"),
    start_date: Optional[str] = Query(
        None, description="Start date filter (ISO format)"
    ),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    sort: Optional[str] = Query("timestamp", description="Sort field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
):
    """
    Get operation history with filtering and pagination

    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        operation_type: Filter by operation type
        task_id: Filter by task ID
        user_id: Filter by user ID
        status: Filter by operation status
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        sort: Field to sort by
        order: Sort order (asc/desc)

    Returns:
        Paginated operation history
    """
    try:
        # Validate pagination parameters
        validated_limit, validated_offset = validate_pagination_params(limit, offset)

        async with get_async_db() as db:
            # Build base query
            query = select(OperationHistory)
            count_query = select(func.count(OperationHistory.id))

            # Apply filters
            filters = []

            if operation_type:
                filters.append(OperationHistory.operation_type == operation_type)

            if task_id:
                filters.append(OperationHistory.task_id == task_id)

            if user_id:
                filters.append(OperationHistory.user_id == user_id)

            if status:
                filters.append(OperationHistory.status == status)

            # Date filters
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    filters.append(OperationHistory.timestamp >= start_dt)
                except ValueError:
                    logger.warning(f"Invalid start_date format: {start_date}")

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    filters.append(OperationHistory.timestamp <= end_dt)
                except ValueError:
                    logger.warning(f"Invalid end_date format: {end_date}")

            # Apply filters to queries
            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))

            # Apply sorting
            if sort in ["timestamp", "operation_type", "status", "duration_ms"]:
                sort_column = getattr(OperationHistory, sort)
                if order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            else:
                # Default sorting by timestamp descending
                query = query.order_by(OperationHistory.timestamp.desc())

            # Get total count
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # Apply pagination
            query = query.offset(validated_offset).limit(validated_limit)
            result = await db.execute(query)
            history_records = result.scalars().all()

            # Convert to response format
            history_list = []
            for record in history_records:
                record_data = record.to_dict()
                # Add task information if available
                if record.task_id:
                    task_result = await db.execute(
                        select(Task).where(Task.task_id == record.task_id)
                    )
                    task = task_result.scalar_one_or_none()
                    if task:
                        record_data["task_info"] = {
                            "status": task.status,
                            "progress": task.progress,
                            "original_filename": task.original_filename,
                        }
                history_list.append(record_data)

            # Calculate pagination info
            has_more = validated_offset + validated_limit < total

            return HistoryListResponse(
                data={
                    "history": history_list,
                    "pagination": {
                        "total": total,
                        "limit": validated_limit,
                        "offset": validated_offset,
                        "has_more": has_more,
                    },
                    "filters_applied": {
                        "operation_type": operation_type,
                        "task_id": task_id,
                        "user_id": user_id,
                        "status": status,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                },
                message=f"Retrieved {len(history_list)} history records",
            )

    except Exception as e:
        logger.error(f"Failed to get operation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_RETRIEVAL_FAILED",
                "message": "Failed to retrieve operation history",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@history_router.get(
    "/history/{history_id}", response_model=HistoryResponse, tags=["History"]
)
async def get_history_detail(
    history_id: int = Path(..., description="History record ID"),
):
    """
    Get detailed information about a specific history record

    Args:
        history_id: ID of the history record

    Returns:
        Detailed history record information

    Raises:
        HTTPException: If history record is not found
    """
    try:
        async with get_async_db() as db:
            result = await db.execute(
                select(OperationHistory).where(OperationHistory.id == history_id)
            )
            history_record = result.scalar_one_or_none()

            if not history_record:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "HISTORY_RECORD_NOT_FOUND",
                        "message": "History record not found",
                        "details": {"history_id": history_id},
                    },
                )

            # Get detailed record data
            record_data = history_record.to_dict()

            # Add related task information if available
            if history_record.task_id:
                task_result = await db.execute(
                    select(Task).where(Task.task_id == history_record.task_id)
                )
                task = task_result.scalar_one_or_none()
                if task:
                    record_data["task_info"] = task.to_dict()

            # Add related history records (same task)
            if history_record.task_id:
                related_result = await db.execute(
                    select(OperationHistory)
                    .where(OperationHistory.task_id == history_record.task_id)
                    .where(OperationHistory.id != history_id)
                    .order_by(OperationHistory.timestamp.desc())
                    .limit(10)
                )
                related_records = related_result.scalars().all()
                record_data["related_operations"] = [
                    {
                        "id": rec.id,
                        "operation_type": rec.operation_type,
                        "status": rec.status,
                        "timestamp": rec.timestamp.isoformat(),
                        "duration_ms": rec.duration_ms,
                    }
                    for rec in related_records
                ]

            return HistoryResponse(
                data=record_data, message="History record retrieved successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get history detail for {history_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_DETAIL_FAILED",
                "message": "Failed to retrieve history record details",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@history_router.get(
    "/history/statistics", response_model=HistoryStatsResponse, tags=["History"]
)
async def get_history_statistics(
    days: Optional[int] = Query(
        7, ge=1, le=90, description="Number of days to analyze"
    ),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
):
    """
    Get operation history statistics and analytics

    Args:
        days: Number of days to analyze (1-90)
        operation_type: Filter by operation type

    Returns:
        History statistics and analytics
    """
    try:
        async with get_async_db() as db:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Build base query
            base_filters = [
                OperationHistory.timestamp >= start_date,
                OperationHistory.timestamp <= end_date,
            ]

            if operation_type:
                base_filters.append(OperationHistory.operation_type == operation_type)

            # Total operations
            total_query = select(func.count(OperationHistory.id)).where(
                and_(*base_filters)
            )
            total_result = await db.execute(total_query)
            total_operations = total_result.scalar() or 0

            # Operations by type
            type_query = (
                select(
                    OperationHistory.operation_type,
                    func.count(OperationHistory.id).label("count"),
                )
                .where(and_(*base_filters))
                .group_by(OperationHistory.operation_type)
            )
            type_result = await db.execute(type_query)
            operations_by_type = dict(type_result.all())

            # Operations by status
            status_query = (
                select(
                    OperationHistory.status,
                    func.count(OperationHistory.id).label("count"),
                )
                .where(and_(*base_filters))
                .group_by(OperationHistory.status)
            )
            status_result = await db.execute(status_query)
            operations_by_status = dict(status_result.all())

            # Average duration by operation type
            duration_query = (
                select(
                    OperationHistory.operation_type,
                    func.avg(OperationHistory.duration_ms).label("avg_duration"),
                )
                .where(and_(*base_filters))
                .where(OperationHistory.duration_ms.isnot(None))
                .group_by(OperationHistory.operation_type)
            )
            duration_result = await db.execute(duration_query)
            avg_duration_by_type = {
                row.operation_type: float(row.avg_duration) for row in duration_result
            }

            # Daily operations count
            daily_query = (
                select(
                    func.date(OperationHistory.timestamp).label("date"),
                    func.count(OperationHistory.id).label("count"),
                )
                .where(and_(*base_filters))
                .group_by(func.date(OperationHistory.timestamp))
                .order_by(func.date(OperationHistory.timestamp))
            )
            daily_result = await db.execute(daily_query)
            daily_operations = [
                {"date": row.date.isoformat(), "count": row.count}
                for row in daily_result
            ]

            # Error rate
            error_filters = base_filters + [OperationHistory.status == "error"]
            error_query = select(func.count(OperationHistory.id)).where(
                and_(*error_filters)
            )
            error_result = await db.execute(error_query)
            error_count = error_result.scalar() or 0
            error_rate = (
                (error_count / total_operations * 100) if total_operations > 0 else 0
            )

            # Most recent operations
            recent_query = (
                select(OperationHistory)
                .where(and_(*base_filters))
                .order_by(OperationHistory.timestamp.desc())
                .limit(5)
            )
            recent_result = await db.execute(recent_query)
            recent_operations = [
                {
                    "id": op.id,
                    "operation_type": op.operation_type,
                    "status": op.status,
                    "timestamp": op.timestamp.isoformat(),
                    "duration_ms": op.duration_ms,
                    "task_id": op.task_id,
                }
                for op in recent_result.scalars().all()
            ]

            statistics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "total_operations": total_operations,
                "operations_by_type": operations_by_type,
                "operations_by_status": operations_by_status,
                "avg_duration_by_type_ms": avg_duration_by_type,
                "daily_operations": daily_operations,
                "error_rate_percent": round(error_rate, 2),
                "recent_operations": recent_operations,
            }

            return HistoryStatsResponse(
                data=statistics, message="History statistics retrieved successfully"
            )

    except Exception as e:
        logger.error(f"Failed to get history statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_STATS_FAILED",
                "message": "Failed to retrieve history statistics",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@history_router.delete(
    "/history/cleanup", response_model=HistoryResponse, tags=["History"]
)
async def cleanup_history(
    days: int = Query(
        30, ge=1, le=365, description="Delete records older than this many days"
    ),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Clean up old operation history records

    Args:
        days: Delete records older than this many days (1-365)
        operation_type: Filter by operation type
        status: Filter by status

    Returns:
        Cleanup operation results
    """
    try:
        async with get_async_db() as db:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Build delete query
            delete_filters = [OperationHistory.timestamp < cutoff_date]

            if operation_type:
                delete_filters.append(OperationHistory.operation_type == operation_type)

            if status:
                delete_filters.append(OperationHistory.status == status)

            # Count records to be deleted
            count_query = select(func.count(OperationHistory.id)).where(
                and_(*delete_filters)
            )
            count_result = await db.execute(count_query)
            records_to_delete = count_result.scalar() or 0

            if records_to_delete == 0:
                return HistoryResponse(
                    data={
                        "records_deleted": 0,
                        "cutoff_date": cutoff_date.isoformat(),
                        "filters_applied": {
                            "days": days,
                            "operation_type": operation_type,
                            "status": status,
                        },
                    },
                    message="No records found for cleanup",
                )

            # Delete records
            delete_query = OperationHistory.__table__.delete().where(
                and_(*delete_filters)
            )
            await db.execute(delete_query)
            await db.commit()

            return HistoryResponse(
                data={
                    "records_deleted": records_to_delete,
                    "cutoff_date": cutoff_date.isoformat(),
                    "filters_applied": {
                        "days": days,
                        "operation_type": operation_type,
                        "status": status,
                    },
                },
                message=f"Successfully deleted {records_to_delete} history records",
            )

    except Exception as e:
        logger.error(f"Failed to cleanup history: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_CLEANUP_FAILED",
                "message": "Failed to cleanup history records",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@history_router.get("/history/export", response_model=HistoryResponse, tags=["History"])
async def export_history(
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    days: Optional[int] = Query(7, ge=1, le=90, description="Number of days to export"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
):
    """
    Export operation history data

    Args:
        format: Export format (json or csv)
        days: Number of days to export (1-90)
        operation_type: Filter by operation type

    Returns:
        Exported history data
    """
    try:
        async with get_async_db() as db:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Build query
            filters = [
                OperationHistory.timestamp >= start_date,
                OperationHistory.timestamp <= end_date,
            ]

            if operation_type:
                filters.append(OperationHistory.operation_type == operation_type)

            query = (
                select(OperationHistory)
                .where(and_(*filters))
                .order_by(OperationHistory.timestamp.desc())
            )

            result = await db.execute(query)
            records = result.scalars().all()

            # Convert to export format
            export_data = []
            for record in records:
                record_dict = record.to_dict()
                # Convert datetime objects to ISO strings
                record_dict["timestamp"] = record.timestamp.isoformat()
                export_data.append(record_dict)

            return HistoryResponse(
                data={
                    "export_format": format,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": days,
                    },
                    "total_records": len(export_data),
                    "data": export_data if format == "json" else None,
                    "csv_ready": format == "csv",
                },
                message=f"Exported {len(export_data)} history records in {format} format",
            )

    except Exception as e:
        logger.error(f"Failed to export history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_EXPORT_FAILED",
                "message": "Failed to export history data",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )
