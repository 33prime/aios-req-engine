"""Archive and restore prototype build sources via Supabase Storage.

After a build completes, source files are archived to Supabase Storage so they
survive /tmp cleanup.  Before an update pipeline runs, if the local build dir
is gone, we restore from the archive.
"""

from __future__ import annotations

import io
import logging
import subprocess
import tarfile
from pathlib import Path
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

BUCKET = "prototype-sources"
CONFIG_FILES = [
    "package.json",
    "vite.config.ts",
    "tsconfig.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "index.html",
    "postcss.config.js",
    "postcss.config.mjs",
]
SOURCE_DIRS = ["src", "public"]
EXCLUDE_DIRS = {"node_modules", "dist", ".git", ".cache", ".next"}


def _tar_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    """Exclude heavy/irrelevant directories."""
    parts = Path(tarinfo.name).parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return None
    return tarinfo


def _ensure_bucket() -> None:
    """Create the storage bucket if it doesn't exist (idempotent)."""
    supabase = get_supabase()
    try:
        supabase.storage.get_bucket(BUCKET)
    except Exception:
        try:
            supabase.storage.create_bucket(
                BUCKET,
                options={
                    "public": False,
                    "file_size_limit": 10485760,  # 10MB
                },
            )
            logger.info(f"Created storage bucket: {BUCKET}")
        except Exception as e:
            # Bucket may already exist from migration — ignore conflict
            if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                raise


def archive_build_source(build_id: UUID, build_dir: str | Path) -> str | None:
    """Archive build source files to Supabase Storage.

    Returns the storage path on success, None on failure.
    Never raises — archival is non-critical.
    """
    build_dir = Path(build_dir)
    if not build_dir.exists():
        logger.warning(f"Build dir does not exist, skipping archive: {build_dir}")
        return None

    try:
        _ensure_bucket()

        # Create tar.gz in memory
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            # Add source directories
            for dir_name in SOURCE_DIRS:
                dir_path = build_dir / dir_name
                if dir_path.exists():
                    tar.add(str(dir_path), arcname=dir_name, filter=_tar_filter)

            # Add config files
            for config_file in CONFIG_FILES:
                file_path = build_dir / config_file
                if file_path.exists():
                    tar.add(str(file_path), arcname=config_file)

        archive_bytes = buf.getvalue()
        storage_path = f"builds/{build_id}.tar.gz"

        supabase = get_supabase()
        supabase.storage.from_(BUCKET).upload(
            path=storage_path,
            file=archive_bytes,
            file_options={
                "content-type": "application/gzip",
                "upsert": "true",
            },
        )

        size_kb = len(archive_bytes) / 1024
        logger.info(f"Archived build {build_id} to {storage_path} ({size_kb:.0f}KB)")
        return storage_path

    except Exception as e:
        logger.warning(f"Source archival failed for build {build_id}: {e}")
        return None


def restore_build_source(build_id: UUID, storage_path: str, restore_dir: Path) -> Path:
    """Restore build source files from Supabase Storage.

    Downloads the archive, extracts it, and runs npm install.
    Raises RuntimeError on failure (restore IS critical).
    """
    try:
        supabase = get_supabase()
        data = supabase.storage.from_(BUCKET).download(storage_path)

        restore_dir.mkdir(parents=True, exist_ok=True)

        # Extract with path traversal protection
        buf = io.BytesIO(data)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise RuntimeError(f"Unsafe path in archive: {member.name}")
            tar.extractall(path=str(restore_dir))

        logger.info(f"Extracted archive to {restore_dir}")

        # Recreate node_modules
        result = subprocess.run(
            ["npm", "install", "--prefer-offline"],
            cwd=str(restore_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"npm install failed: {result.stderr[:500]}")

        logger.info(f"Restored build {build_id} to {restore_dir}")
        return restore_dir

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to restore build {build_id}: {e}") from e
