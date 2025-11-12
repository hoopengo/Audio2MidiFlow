from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

# Check database connection first
from ..database import check_database_health, get_async_db
from ..models import OperationHistory, OperationType, Task
from ..tasks.manager import get_task_manager
from ..utils import get_file_handler, validate_mp3_file
from ..utils.logging import log_task_event

upload_router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for file upload"""

    success: bool = True
    data: Dict[str, Any]
    message: str


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = False
    error: Dict[str, Any]


@upload_router.post(
    "/upload",
    response_model=UploadResponse,
    tags=["Upload"],
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {
                                "type": "string",
                                "format": "binary",
                                "description": "MP3 audio file (max 50MB)",
                            }
                        },
                        "required": ["file"],
                    }
                }
            }
        }
    },
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="MP3 audio file to convert"),
):
    """
    Upload MP3 file for conversion to MIDI

    Args:
        file: MP3 file to upload (max 50MB)

    Returns:
        Task information and initial status

    Raises:
        HTTPException: If file validation fails
    """
    try:
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

        # Log request details for debugging
        logger.info(
            f"Upload request received: filename={file.filename}, content_type={file.content_type}, size={getattr(file, 'size', 'unknown')}"
        )

        # Log additional file attributes
        logger.debug(f"File object attributes: {dir(file)}")
        logger.debug(f"File headers: {getattr(file, 'headers', 'No headers')}")
        logger.debug(f"File content type: {file.content_type}")
        logger.debug(f"File filename: {file.filename}")
        logger.debug(f"File file object: {file.file}")

        # Check if file is actually provided
        if not file or not file.filename:
            logger.error("No file provided or filename is empty")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "NO_FILE_PROVIDED",
                    "message": "No file was provided in the request",
                    "details": {
                        "file_object": str(file),
                        "filename": file.filename if file else None,
                    },
                },
            )

        # Validate uploaded file
        logger.info("Starting file validation")
        file_content, file_size = await validate_mp3_file(file)
        logger.info(f"File validation completed successfully: {file_size} bytes")

        # Get file handler
        file_handler = get_file_handler()

        # Save uploaded file
        input_path, sanitized_filename = await file_handler.save_uploaded_file(
            file_content=file_content,
            original_filename=file.filename or "unknown.mp3",
            file_size=file_size,
        )

        # Create task record
        async with get_async_db() as db:
            task = Task.create_new(
                filename=sanitized_filename, input_path=input_path, file_size=file_size
            )

            db.add(task)
            await db.commit()
            await db.refresh(task)

            # Log file upload operation
            operation = OperationHistory.log_success(
                task_id=task.task_id,
                operation=OperationType.FILE_UPLOAD,
                details=f"File uploaded successfully: {sanitized_filename}",
                operation_metadata={
                    "original_filename": file.filename,
                    "sanitized_filename": sanitized_filename,
                    "file_size": file_size,
                    "content_type": file.content_type,
                },
            )

            db.add(operation)
            await db.commit()

        # Start background processing using shared manager
        task_manager = get_task_manager()
        background_tasks.add_task(task_manager.process_task, task.task_id)

        # Log task creation event
        log_task_event(
            task_logger=logger,
            task_id=task.task_id,
            event="task_created",
            status="pending",
            details={"filename": sanitized_filename, "file_size": file_size},
        )

        logger.info(f"Task created successfully: {task.task_id}")

        return UploadResponse(
            data={
                "task_id": task.task_id,
                "status": task.status,
                "original_filename": sanitized_filename,
                "file_size": file_size,
                "created_at": task.created_at.isoformat(),
                "estimated_processing_time": 120,  # 2 minutes estimate
            },
            message="File uploaded successfully",
        )

    except HTTPException as http_exc:
        # Log HTTP exceptions with more details
        logger.error(
            f"HTTP exception during file upload: {http_exc.status_code} - {http_exc.detail}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "UPLOAD_FAILED",
                "message": "Failed to upload file",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@upload_router.post("/upload/batch", response_model=UploadResponse, tags=["Upload"])
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Multiple MP3 files to convert"),
):
    """
    Upload multiple MP3 files for batch conversion

    Args:
        files: List of MP3 files to upload (max 10 files)

    Returns:
        List of task information

    Raises:
        HTTPException: If validation fails or too many files
    """
    try:
        # Validate number of files
        max_files = 10
        if len(files) > max_files:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "TOO_MANY_FILES",
                    "message": f"Maximum {max_files} files allowed per batch",
                    "details": {"max_files": max_files, "received_files": len(files)},
                },
            )

        # Process each file
        task_manager = get_task_manager()
        created_tasks = []

        async with get_async_db() as db:
            for file in files:
                try:
                    # Validate file
                    file_content, file_size = await validate_mp3_file(file)

                    # Save file
                    file_handler = get_file_handler()
                    (
                        input_path,
                        sanitized_filename,
                    ) = await file_handler.save_uploaded_file(
                        file_content=file_content,
                        original_filename=file.filename or "unknown.mp3",
                        file_size=file_size,
                    )

                    # Create task
                    task = Task.create_new(
                        filename=sanitized_filename,
                        input_path=input_path,
                        file_size=file_size,
                    )

                    db.add(task)
                    await db.flush()

                    # Log operation
                    operation = OperationHistory.log_success(
                        task_id=task.task_id,
                        operation=OperationType.FILE_UPLOAD,
                        details=f"Batch upload: {sanitized_filename}",
                        operation_metadata={
                            "original_filename": file.filename,
                            "sanitized_filename": sanitized_filename,
                            "file_size": file_size,
                            "batch_upload": True,
                        },
                    )

                    db.add(operation)

                    created_tasks.append(
                        {
                            "task_id": task.task_id,
                            "status": task.status,
                            "original_filename": sanitized_filename,
                            "file_size": file_size,
                        }
                    )

                    # Start background processing
                    background_tasks.add_task(task_manager.process_task, task.task_id)

                    logger.info(f"Batch task created: {task.task_id}")

                except HTTPException as e:
                    # Continue with other files if one fails
                    logger.warning(
                        f"Failed to process file {file.filename}: {e.detail}"
                    )
                    created_tasks.append({"error": e.detail, "filename": file.filename})

            await db.commit()

        return UploadResponse(
            data={
                "tasks": created_tasks,
                "total_files": len(files),
                "successful_uploads": len([t for t in created_tasks if "task_id" in t]),
                "failed_uploads": len([t for t in created_tasks if "error" in t]),
            },
            message=f"Processed {len(files)} files",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during batch upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "BATCH_UPLOAD_FAILED",
                "message": "Failed to process batch upload",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@upload_router.get("/upload/status", tags=["Upload"])
async def get_upload_status():
    """
    Get upload service status

    Returns:
        Upload service status and statistics
    """
    try:
        file_handler = get_file_handler()
        storage_info = await file_handler.get_storage_info()

        return {
            "status": "healthy",
            "max_file_size": get_file_handler().settings.max_file_size,
            "supported_formats": ["audio/mpeg", "audio/mp3"],
            "storage_info": storage_info,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get upload status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "STATUS_CHECK_FAILED",
                "message": "Failed to get upload status",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )


@upload_router.delete("/upload/cleanup", tags=["Upload"])
async def cleanup_uploads():
    """
    Clean up old uploaded files

    Returns:
        Cleanup operation results
    """
    try:
        file_handler = get_file_handler()
        cleaned_files = await file_handler.cleanup_temp_files()

        return {
            "success": True,
            "message": f"Cleaned up {cleaned_files} temporary files",
            "cleaned_files": cleaned_files,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cleanup uploads: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CLEANUP_FAILED",
                "message": "Failed to cleanup uploads",
                "details": str(e) if logger.level == "DEBUG" else None,
            },
        )
