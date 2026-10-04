import asyncio
from pathlib import Path

from pyrogram.errors import FloodWait


async def upload_file(
    client,
    chat_id: int,
    path: Path,
    reply_to: int,
    progress_callback,
    retries: int = 3,
):
    attempt = 0
    while True:
        try:
            return await client.send_document(
                chat_id,
                str(path),
                force_document=True,
                reply_to_message_id=reply_to,
                progress=progress_callback,
            )
        except FloodWait as exc:
            attempt += 1
            if attempt > retries:
                raise
            await asyncio.sleep(min(max(int(exc.value), 1), 300))
