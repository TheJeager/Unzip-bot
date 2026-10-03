import os
import sys
from pathlib import Path

def main() -> int:
    required = ("API_ID", "API_HASH", "BOT_TOKEN")
    missing = [name for name in required if not os.getenv(name)]
    temp_dir = Path(os.getenv("TEMP_DOWNLOAD_DIRECTORY", "./temp_downloads"))
    if missing:
        print("missing required environment variables: " + ", ".join(missing))
        return 1
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True, exist_ok=True)
    if not temp_dir.is_dir():
        print("temporary directory is not a directory")
        return 1
    if not os.access(temp_dir, os.W_OK):
        print("temporary directory is not writable")
        return 1
    print("ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
