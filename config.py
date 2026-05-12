import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

TEMP_DOWNLOAD_DIRECTORY = os.getenv(
    "TEMP_DOWNLOAD_DIRECTORY",
    "./temp_downloads"
)

MAX_ARCHIVE_SIZE_MB = int(
    os.getenv("MAX_ARCHIVE_SIZE_MB", "5090")
)

MONGODB_URI = os.getenv("MONGODB_URI", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))
START_IMAGE_URL = ("https://i.ibb.co/4wb2mXMS/photo-2026-05-11-06-56-44.jpg")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError(
        "API_ID, API_HASH, and BOT_TOKEN must be configured."
    )
