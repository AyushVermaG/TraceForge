"""Secure ZIP archive handler with ZipSlip defense and resource bounding."""
import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import List, Tuple, Set
from fastapi import UploadFile, HTTPException
from app.config import settings

logger = logging.getLogger("TraceForge.ZipHandler")

IGNORED_DIRECTORIES: Set[str] = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "ENV",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".tox", ".eggs", "build", "dist"
}

IGNORED_FILE_EXTENSIONS: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".zip", ".tar", ".gz", ".7z", ".rar"
}

def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """ZipSlip protection: Ensure resolved target is within base directory."""
    base_dir = base_dir.resolve()
    target_path = target_path.resolve()
    return base_dir in target_path.parents or base_dir == target_path

class SecureZipExtractor:
    """Safely extracts and filters Python project ZIP files."""

    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.repo_dir = settings.storage_path / repo_id
        self.source_dir = self.repo_dir / "source"

    async def extract_upload(self, upload_file: UploadFile) -> Tuple[Path, List[str]]:
        """Validate, bound, and securely extract uploaded ZIP file."""
        warnings: List[str] = []
        
        # Verify file extension
        filename = upload_file.filename or "repository.zip"
        if not filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only .zip repository archives are supported")

        # Create destination directories
        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir)
        self.source_dir.mkdir(parents=True, exist_ok=True)

        zip_dest = self.repo_dir / "archive.zip"
        total_uploaded_bytes = 0
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        # Stream save archive with size limit
        try:
            with open(zip_dest, "wb") as buffer:
                while chunk := await upload_file.read(1024 * 64): # 64KB chunks
                    total_uploaded_bytes += len(chunk)
                    if total_uploaded_bytes > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Archive exceeds maximum allowable size of {settings.MAX_UPLOAD_SIZE_MB}MB"
                        )
                    buffer.write(chunk)
        except Exception:
            if self.repo_dir.exists():
                shutil.rmtree(self.repo_dir)
            raise

        # Inspect and extract ZIP safely
        try:
            with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
                infolist = zip_ref.infolist()
                
                # Check file count limit
                if len(infolist) > settings.MAX_FILES_COUNT:
                    raise HTTPException(
                        status_code=400,
                        detail=f"ZIP archive contains {len(infolist)} entries, exceeding safety limit of {settings.MAX_FILES_COUNT}"
                    )

                total_uncompressed_bytes = 0
                max_uncompressed_bytes = settings.MAX_TOTAL_UNCOMPRESSED_MB * 1024 * 1024

                for member in infolist:
                    total_uncompressed_bytes += member.file_size
                    if total_uncompressed_bytes > max_uncompressed_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Uncompressed archive exceeds safety footprint of {settings.MAX_TOTAL_UNCOMPRESSED_MB}MB"
                        )

                    # ZipSlip verification
                    target_dest = self.source_dir / member.filename
                    if not is_safe_path(self.source_dir, target_dest):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Illegal path traversal detected in ZIP entry: {member.filename}"
                        )

                # Safe extract
                zip_ref.extractall(self.source_dir)
                logger.info(f"Safely extracted {len(infolist)} entries to {self.source_dir}")

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Malformed or corrupt ZIP archive")
        finally:
            # Clean up uploaded archive zip to save disk space
            if zip_dest.exists():
                zip_dest.unlink()

        # Check if archive extracted into a single top-level root folder
        extracted_items = list(self.source_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            # Flatten one level so root contains the actual code
            root_dir = extracted_items[0]
            temp_dir = self.repo_dir / "temp_flatten"
            root_dir.rename(temp_dir)
            self.source_dir.rmdir()
            temp_dir.rename(self.source_dir)

        return self.source_dir, warnings

    def list_python_files(self) -> List[Path]:
        """Scan extracted source directory, filtering out ignored folders and files."""
        py_files: List[Path] = []
        for root, dirs, files in os.walk(self.source_dir):
            # In-place directory exclusion
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")]
            
            for file in files:
                ext = Path(file).suffix.lower()
                if ext == ".py":
                    py_files.append(Path(root) / file)
        return py_files
