import asyncio
from telethon import events

from ..config import SETTINGS

async def admin(event, db, queue):
    if event.sender_id != SETTINGS.owner_id:
        return
    state = queue.status()
    values = await db.snapshot()
    await event.respond(f"**{SETTINGS.app_name} • Owner Panel**\n\nUsers: **{await db.user_count()}**\nActive: **{state['active']}**\nWaiting: **{state['queued']}**\nSuccessful: **{values.get('successful_jobs',0)}**\nFailed: **{values.get('failed_jobs',0)}**\nRejected: **{values.get('rejected_jobs',0)}**")

async def broadcast(event, db, client):
    if event.sender_id != SETTINGS.owner_id:
        return
    text = event.pattern_match.group(1)
    if not text:
        await event.respond("Usage: /broadcast <message>")
        return
    sent = 0
    async for user_id in db.user_ids():
        try:
            await client.send_message(user_id, text)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await event.respond(f"📣 Broadcast delivered to **{sent}** users.")

def register(client, db, queue):
    client.add_event_handler(lambda event: admin(event, db, queue), events.NewMessage(pattern=r"^/admin(?:@\w+)?$"))
    client.add_event_handler(lambda event: broadcast(event, db, client), events.NewMessage(pattern=r"^/broadcast(?:@\w+)?\s+(.+)$"))
