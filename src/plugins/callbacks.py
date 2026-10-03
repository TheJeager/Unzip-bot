from telethon import Button, events

from .start import buttons, home_text
from ..config import SETTINGS

async def callback(event, db):
    data = event.data.decode()
    user = await db.user(event.sender_id)
    if data == "home":
        name = getattr(event.sender, "first_name", None) or "there"
        await event.edit(home_text(name), buttons=buttons())
    elif data == "help":
        await event.edit(f"**{SETTINGS.app_name} • Help**\n\n/start — Control panel\n/help — Help center\n/settings — Preferences\n/queue — Queue status\n/cancel — Cancel waiting jobs\n/stats — Statistics\n\nSupported: ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ and TXZ.\n\nSecurity limits cover archive size, expanded size, file count, per-file size, compression ratio, path traversal and special files.",buttons=[[Button.inline("‹ Back",b"home")]])
    elif data == "commands":
        await event.edit("**Commands**\n\n/start\n/help\n/settings\n/queue\n/cancel\n/stats\n\nOwner: /admin and /broadcast",buttons=[[Button.inline("‹ Back",b"home")]])
    elif data == "privacy":
        await event.edit("**Privacy**\n\nTemporary archive data is processed locally and removed after the job. MongoDB stores only preferences, job metadata and aggregate counters when configured.",buttons=[[Button.inline("‹ Back",b"home")]])
    elif data == "settings":
        value = bool(user.get("auto_delete", True))
        await event.edit(f"**Settings**\n\nAuto-delete: **{'ON' if value else 'OFF'}**",buttons=[[Button.inline(f"🧹 Auto-delete: {'ON' if value else 'OFF'}",b"toggle_delete")],[Button.inline("‹ Back",b"home")]])
    elif data == "toggle_delete":
        value = not bool(user.get("auto_delete", True))
        await db.update_user(event.sender_id, {"auto_delete": value})
        await event.edit(f"**Settings**\n\nAuto-delete: **{'ON' if value else 'OFF'}**",buttons=[[Button.inline(f"🧹 Auto-delete: {'ON' if value else 'OFF'}",b"toggle_delete")],[Button.inline("‹ Back",b"home")]])
    await event.answer()

def register(client, db):
    client.add_event_handler(lambda event: callback(event, db), events.CallbackQuery())
