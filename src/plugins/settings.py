from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def settings_markup(value: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🧹 Auto-delete: {'ON' if value else 'OFF'}",
            callback_data="toggle_delete",
            style=ButtonStyle.SUCCESS if value else ButtonStyle.DANGER,
        )],
        [InlineKeyboardButton("‹ Back", callback_data="home", style=ButtonStyle.DEFAULT)],
    ])

async def settings(client: Client, message, db) -> None:
    user = await db.user(message.from_user.id)
    value = bool(user.get("auto_delete", True))
    await message.reply_text(
        f"""**Settings**

🧹 Auto-delete bot messages: **{'ON' if value else 'OFF'}**
⏱ Cleanup window is configured by the deployment.""",
        reply_markup=settings_markup(value),
    )

def register(client: Client, db) -> None:
    async def handler(client: Client, message):
        await settings(client, message, db)
    client.add_handler(MessageHandler(handler, filters.command("settings")))
