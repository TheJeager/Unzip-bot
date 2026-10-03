import asyncio
from pathlib import Path

async def delayed_message_cleanup(client, chat_id: int, message_ids: list[int], hours: int) -> None:
    await asyncio.sleep(max(0, hours) * 3600)
    try:
        await client.delete_messages(chat_id, list(dict.fromkeys(message_ids)))
    except Exception:
        pass
