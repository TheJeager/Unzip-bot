from telethon import Button, events

async def settings(event, db):
    user = await db.user(event.sender_id)
    value = bool(user.get("auto_delete", True))
    await event.respond(f"**Settings**\n\n🧹 Auto-delete bot messages: **{'ON' if value else 'OFF'}**\n⏱ Cleanup window is configured by the deployment.",buttons=[[Button.inline(f"🧹 Auto-delete: {'ON' if value else 'OFF'}",b"toggle_delete")],[Button.inline("‹ Back",b"home")]])

def register(client, db):
    async def handler(event):
        await settings(event, db)
    client.add_event_handler(handler, events.NewMessage(pattern=r"^/settings(?:@\w+)?$"))
