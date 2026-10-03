from pyrogram import Client
from pyrogram.enums import ButtonStyle
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .start import buttons, home_text
from .settings import settings_markup
from ..config import SETTINGS

def back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="home", style=ButtonStyle.DEFAULT)]
    ])

async def callback(client: Client, query, db) -> None:
    data = query.data or ""
    user = await db.user(query.from_user.id)

    if data == "home":
        await query.message.edit_text(home_text(query.from_user.first_name or "there"), reply_markup=buttons())
    elif data == "help":
        await query.message.edit_text(
            f"**{SETTINGS.app_name} • Help**

/start — Control panel
/help — Help center
/settings — Preferences
/queue — Queue status
/cancel — Cancel waiting jobs
/stats — Statistics

Supported: ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ and TXZ.

Security limits cover archive size, expanded size, file count, per-file size, compression ratio, path traversal and special files.",
            reply_markup=back_markup(),
        )
    elif data == "commands":
        await query.message.edit_text(
            "**Commands**

/start
/help
/settings
/queue
/cancel
/stats

Owner: /admin and /broadcast",
            reply_markup=back_markup(),
        )
    elif data == "privacy":
        await query.message.edit_text(
            "**Privacy**

Temporary archive data is processed locally and removed after the job. MongoDB stores only preferences, job metadata and aggregate counters when configured.",
            reply_markup=back_markup(),
        )
    elif data == "settings":
        value = bool(user.get("auto_delete", True))
        await query.message.edit_text(
            f"**Settings**

Auto-delete: **{'ON' if value else 'OFF'}**",
            reply_markup=settings_markup(value),
        )
    elif data == "toggle_delete":
        value = not bool(user.get("auto_delete", True))
        await db.update_user(query.from_user.id, {"auto_delete": value})
        await query.message.edit_text(
            f"**Settings**

Auto-delete: **{'ON' if value else 'OFF'}**",
            reply_markup=settings_markup(value),
        )

    await query.answer()

def register(client: Client, db) -> None:
    async def handler(client: Client, query):
        await callback(client, query, db)
    client.add_handler(CallbackQueryHandler(handler))
