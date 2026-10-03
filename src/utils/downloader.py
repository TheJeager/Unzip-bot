from pathlib import Path

async def download_media(client, message, destination: Path, progress_callback):
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = await client.download_media(message, file=str(destination), progress_callback=progress_callback)
    if not result or not destination.exists():
        raise RuntimeError("Archive download failed.")
    return destination
