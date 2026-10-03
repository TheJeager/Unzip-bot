from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import SETTINGS

def buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Help", callback_data="help", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings", style=ButtonStyle.DEFAULT),
        ],
        [
            InlineKeyboardButton("📚 Commands", callback_data="commands", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("🔐 Privacy", callback_data="privacy", style=ButtonStyle.DEFAULT),
        ],
    ])

def home_text(name: str) -> str:
    return f"**{SETTINGS.app_name}**

Welcome, **{name}**.

Send a ZIP or TAR-family archive as a document and I will validate, extract and upload its contents securely.

Use /help for limits and commands."

async def start(client: Client, message):
    name = message.from_user.first_name if message.from_user else "there"
    await message.reply_text(home_text(name or "there"), reply_markup=buttons(), disable_web_page_preview=True)

def register(client: Client) -> None:
    client.add_handler(MessageHandler(start, filters.command("start")))
