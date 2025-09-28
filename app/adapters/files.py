"""File storage adapter."""

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from app.core.config import settings
from app.core.errors import AIError


class FileStorageError(AIError):
    """File storage related errors."""

    def __init__(self, message: str):
        super().__init__(message, "FILE_STORAGE_ERROR", 500)


class FileStorageAdapter:
    """File storage adapter for local files."""

    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_file_path(self, filename: str, subfolder: str = "") -> Path:
        """Get full file path."""
        if subfolder:
            path = self.base_path / subfolder
            path.mkdir(exist_ok=True)
        else:
            path = self.base_path

        return path / filename

    async def save_file(
        self,
        filename: str,
        content: bytes,
        subfolder: str = ""
    ) -> str:
        """Save file content."""
        try:
            file_path = self._get_file_path(filename, subfolder)
            file_path.write_bytes(content)
            return str(file_path)
        except Exception as e:
            raise FileStorageError(f"Failed to save file {filename}: {e}")

    async def save_file_from_stream(
        self,
        filename: str,
        stream: BinaryIO,
        subfolder: str = ""
    ) -> str:
        """Save file from stream."""
        try:
            file_path = self._get_file_path(filename, subfolder)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(stream, f)
            return str(file_path)
        except Exception as e:
            raise FileStorageError(f"Failed to save file from stream {filename}: {e}")

    async def read_file(self, filename: str, subfolder: str = "") -> bytes:
        """Read file content."""
        try:
            file_path = self._get_file_path(filename, subfolder)
            if not file_path.exists():
                raise FileNotFoundError(f"File {filename} not found")
            return file_path.read_bytes()
        except FileNotFoundError:
            raise FileStorageError(f"File {filename} not found")
        except Exception as e:
            raise FileStorageError(f"Failed to read file {filename}: {e}")

    async def delete_file(self, filename: str, subfolder: str = "") -> bool:
        """Delete file."""
        try:
            file_path = self._get_file_path(filename, subfolder)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            raise FileStorageError(f"Failed to delete file {filename}: {e}")

    async def file_exists(self, filename: str, subfolder: str = "") -> bool:
        """Check if file exists."""
        file_path = self._get_file_path(filename, subfolder)
        return file_path.exists()

    async def list_files(self, subfolder: str = "") -> list[str]:
        """List files in folder."""
        try:
            path = self.base_path / subfolder if subfolder else self.base_path
            if not path.exists():
                return []
            return [f.name for f in path.iterdir() if f.is_file()]
        except Exception as e:
            raise FileStorageError(f"Failed to list files: {e}")

    async def get_file_info(self, filename: str, subfolder: str = "") -> Optional[dict]:
        """Get file information."""
        try:
            file_path = self._get_file_path(filename, subfolder)
            if not file_path.exists():
                return None

            stat = file_path.stat()
            return {
                "name": filename,
                "path": str(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            }
        except Exception as e:
            raise FileStorageError(f"Failed to get file info {filename}: {e}")

    async def create_temp_file(self, suffix: str = "") -> Tuple[str, str]:
        """Create temporary file and return filename and path."""
        import tempfile

        try:
            fd, path = tempfile.mkstemp(suffix=suffix, dir=str(self.base_path))
            os.close(fd)  # Close file descriptor
            filename = Path(path).name
            return filename, path
        except Exception as e:
            raise FileStorageError(f"Failed to create temp file: {e}")


# Global file storage instance
file_storage = FileStorageAdapter()
