import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def _int(name: str, default: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise ValueError(f"{name} is required")
        value = str(default)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

@dataclass(frozen=True, slots=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    mongo_uri: str
    owner_id: int
    temp_dir: Path
    max_archive_mb: int
    max_extracted_mb: int
    max_file_mb: int
    max_files: int
    max_ratio: int
    max_concurrent_jobs: int
    max_jobs_per_user: int
    auto_delete_hours: int
    progress_interval: float
    start_image_url: str
    app_name: str

    @property
    def max_archive_bytes(self) -> int:
        return self.max_archive_mb * 1024 * 1024

    @property
    def max_extracted_bytes(self) -> int:
        return self.max_extracted_mb * 1024 * 1024

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

SETTINGS = Settings(
    api_id=_int("API_ID"),
    api_hash=os.getenv("API_HASH", "").strip(),
    bot_token=os.getenv("BOT_TOKEN", "").strip(),
    mongo_uri=os.getenv("MONGODB_URI", "").strip(),
    owner_id=_int("OWNER_ID"),
    temp_dir=Path(os.getenv("TEMP_DOWNLOAD_DIRECTORY", "./temp_downloads")),
    max_archive_mb=_int("MAX_ARCHIVE_SIZE_MB", 4096),
    max_extracted_mb=_int("MAX_EXTRACTED_SIZE_MB", 8192),
    max_file_mb=_int("MAX_EXTRACTED_FILE_MB", 2048),
    max_files=_int("MAX_EXTRACTED_FILES", 500),
    max_ratio=_int("MAX_COMPRESSION_RATIO", 200),
    max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 3),
    max_jobs_per_user=_int("MAX_JOBS_PER_USER", 1),
    auto_delete_hours=_int("AUTO_DELETE_HOURS", 4),
    progress_interval=float(os.getenv("PROGRESS_INTERVAL", "1.5")),
    start_image_url=os.getenv("START_IMAGE_URL", "").strip(),
    app_name=os.getenv("APP_NAME", "Unzip Bot").strip() or "Unzip Bot",
)

if SETTINGS.api_id <= 0 or not SETTINGS.api_hash or not SETTINGS.bot_token:
    raise ValueError("API_ID, API_HASH and BOT_TOKEN are required.")

if SETTINGS.owner_id <= 0:
    raise ValueError("OWNER_ID must be a positive integer.")

SETTINGS.temp_dir.mkdir(parents=True, exist_ok=True)

