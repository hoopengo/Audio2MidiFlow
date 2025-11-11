import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile

from ..config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

# Supported MIME types for MP3 files
SUPPORTED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mpg",
    "audio/mpeg3",
    "audio/x-mpeg",
    "audio/x-mp3",
    "audio/mpegurl",
    "audio/x-mpeg-3",
    "audio/mpg3",
    "audio/x-mpg",
    "audio/x-mpegaudio",
    # Some browsers might send generic MIME types
    "application/octet-stream",
    "audio/unknown",
}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".mpeg", ".mpg"}

# MP3 file signature (magic numbers)
MP3_SIGNATURES = [
    b"ID3",  # ID3v2 tag
    b"\xff\xfb",  # MPEG sync word
    b"\xff\xf3",  # MPEG sync word
    b"\xff\xf2",  # MPEG sync word
    b"\xff\xfa",  # MPEG sync word
    b"\xff\xe3",  # MPEG sync word
    b"\xff\xe2",  # MPEG sync word
    b"\xff\xe1",  # MPEG sync word
    b"\xff\xe0",  # MPEG sync word
    b"\xff\xfe",  # MPEG sync word (additional variation)
    b"TAG",  # ID3v1 tag (at the end of file)
]


def validate_file_size(file: UploadFile) -> None:
    """
    Validate file size against maximum allowed size

    Args:
        file: UploadFile object to validate

    Raises:
        HTTPException: If file size exceeds limit
    """
    settings = get_settings()

    # Check if file has size attribute
    if hasattr(file, "size") and file.size is not None:
        file_size = file.size
    else:
        # If size is not available, we'll check during file reading
        return

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": f"File size exceeds maximum limit of {settings.max_file_size} bytes",
                "details": {
                    "max_size": settings.max_file_size,
                    "received_size": file_size,
                },
            },
        )

    logger.debug(f"File size validation passed: {file_size} bytes")


def validate_file_extension(filename: str) -> None:
    """
    Validate file extension

    Args:
        filename: Name of the file to validate

    Raises:
        HTTPException: If file extension is not supported
    """
    if not filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_FILENAME", "message": "Filename cannot be empty"},
        )

    file_ext = Path(filename).suffix.lower()

    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FILE_EXTENSION",
                "message": f"File extension '{file_ext}' is not supported",
                "details": {
                    "supported_extensions": list(SUPPORTED_EXTENSIONS),
                    "received_extension": file_ext,
                },
            },
        )

    logger.debug(f"File extension validation passed: {file_ext}")


def validate_mime_type(file: UploadFile) -> None:
    """
    Validate MIME type of uploaded file

    Args:
        file: UploadFile object to validate

    Raises:
        HTTPException: If MIME type is not supported
    """
    content_type = file.content_type

    if not content_type:
        # Try to guess from filename
        if file.filename:
            content_type, _ = mimetypes.guess_type(file.filename)
        else:
            content_type = None

    # If we have a content type and it's not in the supported list, check if it's a generic type
    if content_type and content_type not in SUPPORTED_MIME_TYPES:
        # Allow generic binary types if the file extension is valid
        if content_type in ["application/octet-stream", "binary/octet-stream"]:
            if (
                file.filename
                and Path(file.filename).suffix.lower() in SUPPORTED_EXTENSIONS
            ):
                logger.debug(
                    f"Accepted generic MIME type for valid extension: {content_type}"
                )
                return

        # Allow unknown MIME types if the file extension is valid
        if content_type in ["audio/unknown", "unknown/unknown"]:
            if (
                file.filename
                and Path(file.filename).suffix.lower() in SUPPORTED_EXTENSIONS
            ):
                logger.debug(
                    f"Accepted unknown MIME type for valid extension: {content_type}"
                )
                return

        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_MIME_TYPE",
                "message": f"MIME type '{content_type}' is not supported",
                "details": {
                    "supported_mime_types": list(SUPPORTED_MIME_TYPES),
                    "received_mime_type": content_type,
                    "suggestion": "Please ensure the file is a valid MP3 audio file",
                },
            },
        )

    logger.debug(f"MIME type validation passed: {content_type}")


async def validate_mp3_header(file_content: bytes) -> None:
    """
    Validate MP3 file header/signature

    Args:
        file_content: First few bytes of the file

    Raises:
        HTTPException: If file signature doesn't match MP3 format
    """
    if not file_content:
        raise HTTPException(
            status_code=400,
            detail={"error": "EMPTY_FILE", "message": "Uploaded file is empty"},
        )

    # Check for MP3 signatures at the beginning of the file
    is_valid_mp3 = False

    # Check for standard MP3 signatures
    for signature in MP3_SIGNATURES:
        if signature == b"TAG":  # ID3v1 tag is at the end, skip for now
            continue
        if signature == b"\xff\xfe":  # Additional pattern
            if (
                len(file_content) >= 2
                and file_content[0] == 0xFF
                and (file_content[1] & 0xE0) == 0xE0
            ):
                is_valid_mp3 = True
                break
        elif file_content.startswith(signature):
            is_valid_mp3 = True
            break

    # If no header signature found, check for ID3v1 tag at the end of file
    if not is_valid_mp3 and len(file_content) > 128:
        if file_content[-128:-125] == b"TAG":
            is_valid_mp3 = True

    # If still not valid, try a more lenient check for MP3 frames
    if not is_valid_mp3 and len(file_content) >= 4:
        # Look for MP3 frame sync patterns anywhere in the first 1KB
        search_area = min(1024, len(file_content))
        for i in range(search_area - 3):
            # Check for MPEG frame sync (11 consecutive bits set)
            if file_content[i] == 0xFF and (file_content[i + 1] & 0xE0) == 0xE0:
                # Additional check for valid MPEG frame header
                if (file_content[i + 1] & 0x18) != 0x08:  # Not a valid MPEG layer
                    continue
                if (file_content[i + 1] & 0x06) == 0x00:  # Not a valid MPEG version
                    continue
                is_valid_mp3 = True
                break

    if not is_valid_mp3:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FILE_FORMAT",
                "message": "File does not appear to be a valid MP3 file",
                "details": {
                    "file_size": len(file_content),
                    "file_start": file_content[:16].hex(),
                    "suggestion": "Please ensure the file is a valid MP3 audio file",
                },
            },
        )

    logger.debug("MP3 header validation passed")


async def validate_mp3_file(file: UploadFile) -> Tuple[bytes, int]:
    """
    Comprehensive MP3 file validation

    Args:
        file: UploadFile object to validate

    Returns:
        Tuple of (file_content, file_size)

    Raises:
        HTTPException: If any validation fails
    """
    logger.info(
        f"Starting validation for file: {file.filename}, content_type: {file.content_type}"
    )

    # Log file object details
    logger.debug(f"File object type: {type(file)}")
    logger.debug(f"File object attributes: {dir(file)}")
    logger.debug(f"File file attribute: {getattr(file, 'file', 'No file attribute')}")
    logger.debug(f"File content_type: {file.content_type}")
    logger.debug(f"File filename: {file.filename}")
    logger.debug(f"File size attribute: {getattr(file, 'size', 'No size attribute')}")

    # Validate filename and extension
    if file.filename:
        logger.info(f"Validating filename: {file.filename}")
        try:
            validate_file_extension(file.filename)
            logger.info("Filename validation passed")
        except HTTPException as e:
            logger.error(f"Filename validation failed: {e.detail}")
            raise
    else:
        logger.warning("No filename provided for validation")

    # Validate MIME type
    logger.info(f"Validating MIME type: {file.content_type}")
    try:
        validate_mime_type(file)
        logger.info("MIME type validation passed")
    except HTTPException as e:
        logger.error(f"MIME type validation failed: {e.detail}")
        raise

    # Read file content for validation
    logger.info("Reading file content for validation")
    try:
        file_content = await file.read()
        file_size = len(file_content)
        logger.info(f"File content read successfully, size: {file_size} bytes")
    except Exception as e:
        logger.error(f"Failed to read file content: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "FILE_READ_ERROR",
                "message": "Failed to read uploaded file content",
                "details": {"error": str(e)},
            },
        )

    # Validate file size
    settings = get_settings()
    logger.info(
        f"Checking file size: {file_size} bytes (max: {settings.max_file_size} bytes)"
    )
    if file_size > settings.max_file_size:
        logger.warning(
            f"File too large: {file_size} bytes, max allowed: {settings.max_file_size} bytes"
        )
        raise HTTPException(
            status_code=413,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": f"File size exceeds maximum limit of {settings.max_file_size} bytes",
                "details": {
                    "max_size": settings.max_file_size,
                    "received_size": file_size,
                },
            },
        )

    # Validate MP3 header
    logger.info("Validating MP3 header")
    try:
        await validate_mp3_header(file_content)
        logger.info("MP3 header validation passed")
    except HTTPException as e:
        logger.error(f"MP3 header validation failed: {e.detail}")
        raise

    # Reset file position for further processing
    logger.info("Resetting file position for further processing")
    try:
        await file.seek(0)
        logger.info("File position reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset file position: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "FILE_SEEK_ERROR",
                "message": "Failed to reset file position after validation",
                "details": {"error": str(e)},
            },
        )

    logger.info(
        f"MP3 file validation successful: {file.filename}, size: {file_size} bytes"
    )

    return file_content, file_size


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for secure storage

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unknown.mp3"

    # Remove path components
    filename = os.path.basename(filename)

    # Remove dangerous characters
    dangerous_chars = ["..", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")

    # Ensure it has a valid extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        filename += ".mp3"

    # Limit filename length
    max_length = 255
    if len(filename) > max_length:
        name_part = Path(filename).stem
        ext_part = Path(filename).suffix
        filename = name_part[: max_length - len(ext_part)] + ext_part

    logger.debug(f"Filename sanitized: {filename}")
    return filename


def validate_task_id(task_id: str) -> None:
    """
    Validate task ID format

    Args:
        task_id: Task ID to validate

    Raises:
        HTTPException: If task ID format is invalid
    """
    try:
        # Try to parse as UUID
        uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_TASK_ID",
                "message": "Task ID must be a valid UUID",
                "details": {"received_task_id": task_id, "expected_format": "UUID v4"},
            },
        )

    logger.debug(f"Task ID validation passed: {task_id}")


def validate_pagination_params(
    limit: Optional[int] = None, offset: Optional[int] = None
) -> Tuple[int, int]:
    """
    Validate pagination parameters

    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        Tuple of (validated_limit, validated_offset)

    Raises:
        HTTPException: If parameters are invalid
    """
    # Default values
    default_limit = 20
    max_limit = 100

    # Validate limit
    if limit is None:
        validated_limit = default_limit
    else:
        if limit < 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_LIMIT",
                    "message": "Limit must be at least 1",
                    "details": {"received_limit": limit},
                },
            )
        elif limit > max_limit:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "LIMIT_TOO_HIGH",
                    "message": f"Limit cannot exceed {max_limit}",
                    "details": {"max_limit": max_limit, "received_limit": limit},
                },
            )
        else:
            validated_limit = limit

    # Validate offset
    if offset is None:
        validated_offset = 0
    else:
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_OFFSET",
                    "message": "Offset cannot be negative",
                    "details": {"received_offset": offset},
                },
            )
        else:
            validated_offset = offset

    logger.debug(
        f"Pagination validated: limit={validated_limit}, offset={validated_offset}"
    )

    return validated_limit, validated_offset
