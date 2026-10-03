import asyncio
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import SETTINGS
from .security import ArchiveSecurityError, is_special_mode, is_symlink_mode, safe_member_path, validate_output_tree

@dataclass(slots=True)
class ArchivePlan:
    files: int
    extracted_bytes: int
    archive_bytes: int

@dataclass(slots=True)
class ExtractionResult:
    files: list[Path]
    extracted_bytes: int
    archive_bytes: int

def archive_kind(filename: str) -> str | None:
    name = filename.lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        return "tar"
    return None

def _limits(files: int, extracted: int, archive_bytes: int) -> None:
    if files > SETTINGS.max_files:
        raise ArchiveSecurityError(f"Archive contains too many files. Limit: {SETTINGS.max_files}.")
    if extracted > SETTINGS.max_extracted_mb * 1024 * 1024:
        raise ArchiveSecurityError(f"Expanded archive exceeds {SETTINGS.max_extracted_mb} MB.")
    if archive_bytes > SETTINGS.max_archive_mb * 1024 * 1024:
        raise ArchiveSecurityError(f"Archive exceeds {SETTINGS.max_archive_mb} MB.")
    if archive_bytes and extracted / archive_bytes > SETTINGS.max_ratio:
        raise ArchiveSecurityError(f"Compression ratio exceeds {SETTINGS.max_ratio}x.")

def inspect_zip(path: Path) -> ArchivePlan:
    archive_bytes = path.stat().st_size
    files = 0
    extracted = 0
    seen: set[str] = set()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            mode = member.external_attr >> 16
            if is_symlink_mode(mode) or is_special_mode(mode):
                raise ArchiveSecurityError(f"Unsupported special entry: {member.filename}")
            safe_member_path(Path("/tmp"), member.filename)
            normalized = member.filename.replace("\\", "/")
            if normalized in seen:
                raise ArchiveSecurityError(f"Duplicate archive entry: {member.filename}")
            seen.add(normalized)
            size = int(member.file_size)
            if size < 0:
                raise ArchiveSecurityError("Archive contains an invalid size.")
            if size > SETTINGS.max_file_mb * 1024 * 1024:
                raise ArchiveSecurityError(f"File exceeds {SETTINGS.max_file_mb} MB.")
            files += 1
            extracted += size
    _limits(files, extracted, archive_bytes)
    return ArchivePlan(files, extracted, archive_bytes)

def inspect_tar(path: Path) -> ArchivePlan:
    archive_bytes = path.stat().st_size
    files = 0
    extracted = 0
    seen: set[str] = set()
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if member.issym() or member.islnk() or is_special_mode(member.mode):
                raise ArchiveSecurityError(f"Unsupported special entry: {member.name}")
            safe_member_path(Path("/tmp"), member.name)
            normalized = member.name.replace("\\", "/")
            if normalized in seen:
                raise ArchiveSecurityError(f"Duplicate archive entry: {member.name}")
            seen.add(normalized)
            size = max(0, int(member.size))
            if size > SETTINGS.max_file_mb * 1024 * 1024:
                raise ArchiveSecurityError(f"File exceeds {SETTINGS.max_file_mb} MB.")
            files += 1
            extracted += size
    _limits(files, extracted, archive_bytes)
    return ArchivePlan(files, extracted, archive_bytes)

def inspect(path: Path, filename: str) -> ArchivePlan:
    kind = archive_kind(filename)
    if kind == "zip":
        return inspect_zip(path)
    if kind == "tar":
        return inspect_tar(path)
    raise ArchiveSecurityError("Unsupported archive format.")

def _extract_zip(path: Path, output: Path, callback) -> list[Path]:
    files: list[Path] = []
    done = 0
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            target = safe_member_path(output, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                    done += len(chunk)
                    callback(done)
            files.append(target)
    return files

def _extract_tar(path: Path, output: Path, callback) -> list[Path]:
    files: list[Path] = []
    done = 0
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            target = safe_member_path(output, member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            source = archive.extractfile(member)
            if source is None:
                raise ArchiveSecurityError(f"Unable to read archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                    done += len(chunk)
                    callback(done)
            files.append(target)
    return files

async def extract(path: Path, filename: str, output: Path, callback) -> ExtractionResult:
    plan = inspect(path, filename)
    output.mkdir(parents=True, exist_ok=True)
    kind = archive_kind(filename)
    if kind == "zip":
        files = await asyncio.to_thread(_extract_zip, path, output, callback)
    else:
        files = await asyncio.to_thread(_extract_tar, path, output, callback)
    validate_output_tree(output)
    actual = sum(item.stat().st_size for item in files if item.is_file())
    if actual > SETTINGS.max_extracted_mb * 1024 * 1024:
        raise ArchiveSecurityError("Extracted data exceeded the configured limit.")
    return ExtractionResult(files, actual, plan.archive_bytes)
