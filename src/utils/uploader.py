from pathlib import Path

async def upload_file(client, chat_id: int, path: Path, reply_to: int, progress_callback):
    return await client.send_document(
        chat_id,
        str(path),
        force_document=True,
        reply_to_message_id=reply_to,
        progress=progress_callback,
    )
