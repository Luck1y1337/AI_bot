import os
import zipfile
from aiogram import Bot
from aiogram.types import FSInputFile
from config.settings import get_settings
from database.repository import Database

settings = get_settings()


async def perform_backup(bot: Bot, db: Database):
    if not settings.ADMIN_USER_IDS:
        return

    admin_id = settings.ADMIN_USER_IDS[0]

    os.makedirs("cache/backup", exist_ok=True)
    snapshot = "cache/backup/mahiro.db"
    zip_path = "cache/backup/mahiro_backup.zip"

    try:
        # Consistent snapshot via SQLite's online backup API (safe while the
        # bot keeps running). backup_to requires the dest not to pre-exist.
        if os.path.exists(snapshot):
            os.remove(snapshot)
        await db.backup_to(snapshot)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(snapshot, "mahiro.db")
            if os.path.exists("logs/mahiro.log"):
                zf.write("logs/mahiro.log", "mahiro.log")

        os.remove(snapshot)
        await bot.send_document(
            admin_id, FSInputFile(zip_path),
            caption="📦 Автоматический бэкап базы данных.\n\nЧтобы восстановить: перешли этот файл боту с подписью <code>/restore</code>.",
        )
    except Exception as e:
        await bot.send_message(admin_id, f"⚠️ Ошибка при создании авто-бэкапа: {e}")
