from telethon import Button, events

from ..config import SETTINGS

def buttons():
    return [[Button.inline("📦 Help", b"help"), Button.inline("⚙️ Settings", b"settings")],[Button.inline("📚 Commands", b"commands"), Button.inline("🔐 Privacy", b"privacy")]]

def home_text(name: str) -> str:
    return f"**{SETTINGS.app_name}**\n\nWelcome, **{name}**.\n\nSend a ZIP or TAR-family archive as a document and I will validate, extract and upload its contents securely.\n\nUse /help for limits and commands."

async def start(event):
    name = getattr(event.sender, "first_name", None) or "there"
    await event.respond(home_text(name), buttons=buttons(), link_preview=False)

def register(client):
    client.add_event_handler(start, events.NewMessage(pattern=r"^/start(?:@\w+)?$"))
