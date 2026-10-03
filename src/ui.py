from telethon import Button

from .config import SETTINGS

def start_buttons(agreed: bool) -> list:
    rows = [
        [Button.inline("📦 How It Works", b"help"), Button.inline("⚙️ Settings", b"settings")],
        [Button.inline("🔐 Privacy", b"privacy"), Button.inline("📊 Stats", b"stats")],
    ]
    rows.append([Button.inline("📚 Commands", b"commands")])
    if not agreed:
        rows.append([Button.inline("✅ Accept & Continue", b"agree")])
    return rows

def back_button() -> list:
    return [[Button.inline("‹ Back", b"home")]]

def settings_buttons(auto_delete: bool) -> list:
    state = "ON" if auto_delete else "OFF"
    return [[Button.inline(f"🧹 Auto-delete: {state}", b"toggle_delete")], [Button.inline("‹ Back", b"home")]]

def home_text(name: str, agreed: bool) -> str:
    action = "Send me an archive whenever you're ready." if agreed else "Accept the terms below to enable extraction."
    return (
        f"**{SETTINGS.app_name}**\n\n"
        f"Welcome, **{name}**.\n\n"
        "⚡ Fast archive extraction with a security-first pipeline.\n"
        "📦 ZIP and TAR-family archives\n"
        "🛡️ Path traversal and special-file protection\n"
        "📈 Live download, extraction and upload progress\n"
        "🧹 Automatic temporary-file cleanup\n\n"
        f"{action}\n\n"
        "Use the buttons below or /help for the full command list."
    )

def help_text() -> str:
    return (
        f"**{SETTINGS.app_name} • Help Center**\n\n"
        "**Core Commands**\n"
        "/start — Open the control panel\n"
        "/help — Show detailed help\n"
        "/settings — Configure preferences\n"
        "/stats — View operational statistics\n"
        "/queue — View active and waiting jobs\n"
        "/cancel — Cancel waiting jobs\n\n"
        "**Archive Workflow**\n"
        "Send a supported archive as a document. The bot automatically downloads, validates, extracts and uploads the files.\n\n"
        "**Supported Formats**\n"
        "ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ and TXZ.\n\n"
        "**Protection**\n"
        "Archive size, expanded size, file count, per-file size and compression-ratio limits are enforced. Unsafe paths, symbolic links and special files are rejected.\n\n"
        "**Queue**\n"
        "Jobs are processed by async workers. Each user has an independent concurrency limit and the whole bot has a global worker limit."
    )

def commands_text() -> str:
    return (
        f"**{SETTINGS.app_name} • Commands**\n\n"
        "/start — Control panel\n"
        "/help — Help center\n"
        "/settings — Preferences\n"
        "/stats — Statistics\n"
        "/queue — Queue status\n"
        "/cancel — Cancel waiting jobs\n\n"
        "**Owner**\n"
        "/admin — Owner panel\n"
        "/broadcast <text> — Announcement\n"
        "/maintenance — Maintenance status"
    )

def privacy_text() -> str:
    return (
        f"**{SETTINGS.app_name} • Privacy**\n\n"
        "Archives are processed only for the requested extraction. Temporary working files are removed after the job completes.\n\n"
        "MongoDB stores user preferences, job metadata and aggregate counters when configured. Archive contents are not stored in the database.\n\n"
        "Do not upload sensitive information unless you are comfortable sending it through Telegram."
    )

def settings_text(auto_delete: bool) -> str:
    state = "enabled" if auto_delete else "disabled"
    return (
        f"**{SETTINGS.app_name} • Settings**\n\n"
        f"🧹 Message auto-delete: **{state}**\n"
        f"⏱ Cleanup window: **{SETTINGS.auto_delete_hours} hours**\n\n"
        "Temporary extraction data is always cleaned up. The setting controls deletion of bot messages."
    )
