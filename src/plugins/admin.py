import asyncio

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

from ..config import SETTINGS


async def admin(client: Client, message, db, queue) -> None:
    if not message.from_user or message.from_user.id != SETTINGS.owner_id:
        return
    state = queue.status()
    values = await db.snapshot()
    await message.reply_text(
        f"**{SETTINGS.app_name} • Owner Panel**\n\n"
        f"Users: **{await db.user_count()}**\n"
        f"Active: **{state['active']}**\n"
        f"Waiting: **{state['queued']}**\n"
        f"Successful: **{values.get('successful_jobs', 0)}**\n"
        f"Failed: **{values.get('failed_jobs', 0)}**\n"
        f"Rejected: **{values.get('rejected_jobs', 0)}**"
    )


async def broadcast(client: Client, message, db) -> None:
    if not message.from_user or message.from_user.id != SETTINGS.owner_id:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /broadcast <message>")
        return
    sent = 0
    async for user_id in db.user_ids():
        try:
            await client.send_message(user_id, parts[1])
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await message.reply_text(f"📣 Broadcast delivered to **{sent}** users.")


def register(client: Client, db, queue) -> None:
    async def admin_handler(client: Client, message):
        await admin(client, message, db, queue)

    async def broadcast_handler(client: Client, message):
        await broadcast(client, message, db)

    client.add_handler(MessageHandler(admin_handler, filters.command("admin")))
    client.add_handler(MessageHandler(broadcast_handler, filters.command("broadcast")))
