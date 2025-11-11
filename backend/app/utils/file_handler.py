import asyncio
import hashlib
import shutil
import time
import uuid
from pathlib import Path

import aiofiles

from ..config import get_settings
from .logging import get_logger
from .validators import sanitize_filename

logger = get_logger(__name__)


class FileHandler:
    """Utility class for handling file operations"""

    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = Path(self.settings.upload_dir)
        self.output_dir = Path(self.settings.output_dir)
        self.temp_dir = Path(self.settings.temp_dir)

    async def save_uploaded_file(
        self, file_content: bytes, original_filename: str, file_size: int
    ) -> tuple[str, str]:
        """
        Save uploaded file to storage

        Args:
            file_content: File content as bytes
            original_filename: Original filename
            file_size: Size of the file in bytes

        Returns:
            Tuple of (file_path, sanitized_filename)
        """
        # Generate unique filename
        sanitized_name = sanitize_filename(original_filename)
        unique_filename = f"{uuid.uuid4()}_{sanitized_name}"
        file_path = self.upload_dir / unique_filename

        try:
            # Ensure upload directory exists
            self.upload_dir.mkdir(parents=True, exist_ok=True)

            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)

            logger.info(f"File saved successfully: {file_path} ({file_size} bytes)")
            return str(file_path), unique_filename

        except Exception as e:
            logger.error(f"Failed to save file {original_filename}: {e}")
            raise

    async def save_output_file(
        self, file_content: bytes, task_id: str, extension: str = ".mid"
    ) -> str:
        """
        Save processed output file

        Args:
            file_content: File content as bytes
            task_id: Task identifier
            extension: File extension

        Returns:
            Path to saved file
        """
        filename = f"{task_id}{extension}"
        file_path = self.output_dir / filename

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)

            logger.info(f"Output file saved: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save output file for task {task_id}: {e}")
            raise

    async def read_file(self, file_path: str) -> bytes:
        """
        Read file content asynchronously

        Args:
            file_path: Path to file

        Returns:
            File content as bytes
        """
        try:
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()

            logger.debug(f"File read successfully: {file_path}")
            return content

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage

        Args:
            file_path: Path to file to delete

        Returns:
            True if deletion was successful
        """
        try:
            path = Path(file_path)
            if path.exists():
                await asyncio.to_thread(path.unlink)
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Move file from source to destination

        Args:
            source_path: Current file location
            destination_path: Target file location

        Returns:
            True if move was successful
        """
        try:
            source = Path(source_path)
            destination = Path(destination_path)

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move file asynchronously
            await asyncio.to_thread(shutil.move, str(source), str(destination))

            logger.info(f"File moved: {source_path} -> {destination_path}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to move file {source_path} to {destination_path}: {e}"
            )
            return False

    async def copy_file(self, source_path: str, destination_path: str) -> bool:
        """
        Copy file from source to destination

        Args:
            source_path: Source file location
            destination_path: Target file location

        Returns:
            True if copy was successful
        """
        try:
            source = Path(source_path)
            destination = Path(destination_path)

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file asynchronously
            await asyncio.to_thread(shutil.copy2, str(source), str(destination))

            logger.info(f"File copied: {source_path} -> {destination_path}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to copy file {source_path} to {destination_path}: {e}"
            )
            return False

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash as hexadecimal string
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            hash_hex = sha256_hash.hexdigest()
            logger.debug(f"File hash calculated: {file_path} -> {hash_hex}")
            return hash_hex

        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""

    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        try:
            path = Path(file_path)
            if path.exists():
                size = path.stat().st_size
                logger.debug(f"File size: {file_path} -> {size} bytes")
                return size
            else:
                logger.warning(f"File not found: {file_path}")
                return 0

        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {e}")
            return 0

    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists

        Args:
            file_path: Path to file

        Returns:
            True if file exists
        """
        try:
            exists = Path(file_path).exists()
            logger.debug(f"File existence check: {file_path} -> {exists}")
            return exists

        except Exception as e:
            logger.error(f"Failed to check file existence for {file_path}: {e}")
            return False

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of files cleaned up
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0

            if not self.temp_dir.exists():
                return 0

            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime

                    if file_age > max_age_seconds:
                        await asyncio.to_thread(file_path.unlink)
                        cleaned_count += 1
                        logger.info(f"Cleaned up temp file: {file_path}")

            logger.info(
                f"Temporary file cleanup completed: {cleaned_count} files removed"
            )
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return 0

    async def get_storage_info(self) -> dict:
        """
        Get storage information

        Returns:
            Dictionary with storage statistics
        """
        try:

            def get_dir_size(directory: Path) -> int:
                total_size = 0
                if directory.exists():
                    for file_path in directory.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                return total_size

            upload_size = get_dir_size(self.upload_dir)
            output_size = get_dir_size(self.output_dir)
            temp_size = get_dir_size(self.temp_dir)
            total_size = upload_size + output_size + temp_size

            return {
                "upload_dir": str(self.upload_dir),
                "output_dir": str(self.output_dir),
                "temp_dir": str(self.temp_dir),
                "upload_size_bytes": upload_size,
                "output_size_bytes": output_size,
                "temp_size_bytes": temp_size,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {}

    async def create_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """
        Create a temporary file

        Args:
            content: File content
            suffix: File suffix

        Returns:
            Path to created temporary file
        """
        try:
            # Ensure temp directory exists
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            temp_filename = f"{uuid.uuid4()}{suffix}"
            temp_path = self.temp_dir / temp_filename

            # Save file
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(content)

            logger.debug(f"Temporary file created: {temp_path}")
            return str(temp_path)

        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            raise


# Global file handler instance
file_handler = FileHandler()


def get_file_handler() -> FileHandler:
    """Get global file handler instance"""
    return file_handler
