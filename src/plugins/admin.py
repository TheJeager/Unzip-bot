import asyncio

from pyrogram import Client, filters

from ..config import SETTINGS

async def admin(client: Client, message, db, queue) -> None:
    if message.from_user.id != SETTINGS.owner_id:
        return
    state = queue.status()
    values = await db.snapshot()
    await message.reply_text(
        f"**{SETTINGS.app_name} • Owner Panel**

Users: **{await db.user_count()}**
Active: **{state['active']}**
Waiting: **{state['queued']}**
Successful: **{values.get('successful_jobs', 0)}**
Failed: **{values.get('failed_jobs', 0)}**
Rejected: **{values.get('rejected_jobs', 0)}**"
    )

async def broadcast(client: Client, message, db) -> None:
    if message.from_user.id != SETTINGS.owner_id:
        return
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply_text("Usage: /broadcast <message>")
        return
    sent = 0
    async for user_id in db.user_ids():
        try:
            await client.send_message(user_id, text[1])
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
    client.add_handler(filters.MessageHandler(admin_handler, filters.command("admin")))
    client.add_handler(filters.MessageHandler(broadcast_handler, filters.command("broadcast")))
