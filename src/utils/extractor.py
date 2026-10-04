import asyncio
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..config import SETTINGS
from ..handlers.security import (
    ArchiveSecurityError,
    is_special_mode,
    is_symlink_mode,
    safe_member_path,
    validate_output_tree,
)


@dataclass(slots=True)
class ArchivePlan:
    files: int
    expanded_bytes: int
    archive_bytes: int


@dataclass(slots=True)
class ExtractionResult:
    files: list[Path]
    expanded_bytes: int
    archive_bytes: int


def archive_kind(name: str) -> str | None:
    value = name.lower()
    if value.endswith(".zip"):
        return "zip"
    if value.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        return "tar"
    return None


def _validate(files: int, expanded: int, archive_bytes: int) -> None:
    if archive_bytes > SETTINGS.max_archive_bytes:
        raise ArchiveSecurityError("Archive exceeds the configured size limit.")
    if files > SETTINGS.max_files:
        raise ArchiveSecurityError("Archive contains too many files.")
    if expanded > SETTINGS.max_extracted_bytes:
        raise ArchiveSecurityError("Expanded archive exceeds the configured limit.")
    if archive_bytes and expanded / archive_bytes > SETTINGS.max_ratio:
        raise ArchiveSecurityError("Compression ratio exceeds the configured limit.")


def inspect_zip(path: Path) -> ArchivePlan:
    files = 0
    expanded = 0
    seen = set()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            mode = member.external_attr >> 16
            if is_symlink_mode(mode) or is_special_mode(mode):
                raise ArchiveSecurityError(f"Unsupported archive entry: {member.filename}")
            safe_member_path(Path("/tmp"), member.filename)
            normalized = member.filename.replace("\\", "/")
            if normalized in seen:
                raise ArchiveSecurityError(f"Duplicate archive entry: {member.filename}")
            seen.add(normalized)
            size = int(member.file_size)
            if size < 0 or size > SETTINGS.max_file_bytes:
                raise ArchiveSecurityError(f"File exceeds the configured per-file limit: {member.filename}")
            files += 1
            expanded += size
    archive_bytes = path.stat().st_size
    _validate(files, expanded, archive_bytes)
    return ArchivePlan(files, expanded, archive_bytes)


def inspect_tar(path: Path) -> ArchivePlan:
    files = 0
    expanded = 0
    seen = set()
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if member.issym() or member.islnk() or is_special_mode(member.mode):
                raise ArchiveSecurityError(f"Unsupported archive entry: {member.name}")
            safe_member_path(Path("/tmp"), member.name)
            normalized = member.name.replace("\\", "/")
            if normalized in seen:
                raise ArchiveSecurityError(f"Duplicate archive entry: {member.name}")
            seen.add(normalized)
            size = max(0, int(member.size))
            if size > SETTINGS.max_file_bytes:
                raise ArchiveSecurityError(f"File exceeds the configured per-file limit: {member.name}")
            files += 1
            expanded += size
    archive_bytes = path.stat().st_size
    _validate(files, expanded, archive_bytes)
    return ArchivePlan(files, expanded, archive_bytes)


def inspect(path: Path, filename: str) -> ArchivePlan:
    kind = archive_kind(filename)
    if kind == "zip":
        return inspect_zip(path)
    if kind == "tar":
        return inspect_tar(path)
    raise ArchiveSecurityError("Unsupported archive format.")


def _extract_zip(path: Path, output: Path, callback) -> list[Path]:
    result = []
    done = 0
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            target = safe_member_path(output, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                    done += len(chunk)
                    callback(done)
            result.append(target)
    return result


def _extract_tar(path: Path, output: Path, callback) -> list[Path]:
    result = []
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
            result.append(target)
    return result


async def extract(
    path: Path,
    filename: str,
    output: Path,
    callback,
    plan: ArchivePlan | None = None,
) -> ExtractionResult:
    plan = plan or inspect(path, filename)
    output.mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()

    def report(current: int) -> None:
        loop.call_soon_threadsafe(callback, current)

    if archive_kind(filename) == "zip":
        files = await asyncio.to_thread(_extract_zip, path, output, report)
    else:
        files = await asyncio.to_thread(_extract_tar, path, output, report)

    validate_output_tree(output)
    actual = sum(p.stat().st_size for p in files if p.is_file())
    if actual > SETTINGS.max_extracted_bytes:
        raise ArchiveSecurityError("Extracted data exceeded the configured limit.")
    return ExtractionResult(files, actual, plan.archive_bytes)
