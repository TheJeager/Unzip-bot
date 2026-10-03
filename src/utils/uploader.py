from pathlib import Path

async def upload_file(client, chat_id: int, path: Path, reply_to: int, progress_callback):
    return await client.send_file(chat_id, str(path), force_document=True, allow_cache=False, reply_to=reply_to, progress_callback=progress_callback)
