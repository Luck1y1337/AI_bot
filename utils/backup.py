import os
import zipfile
import shutil
from aiogram import Bot
from config.settings import get_settings

settings = get_settings()

async def perform_backup(bot: Bot):
    if not settings.ADMIN_USER_IDS:
        return
        
    admin_id = settings.ADMIN_USER_IDS[0]
    
    os.makedirs("cache/backup", exist_ok=True)
    zip_path = "cache/backup/mahiro_backup.zip"
    
    # Simple backup of DB and Logs
    try:
        with zipfile.ZipFile(zip_path, 'w') as zf:
            if os.path.exists("data/mahiro.db"):
                # Copy to temp file to avoid lock issues
                shutil.copy2("data/mahiro.db", "cache/backup/mahiro.db")
                zf.write("cache/backup/mahiro.db", "mahiro.db")
                os.remove("cache/backup/mahiro.db")
                
            if os.path.exists("logs/mahiro.log"):
                zf.write("logs/mahiro.log", "mahiro.log")
                
        from aiogram.types import FSInputFile
        await bot.send_document(admin_id, FSInputFile(zip_path), caption="📦 Автоматический бэкап базы данных.")
    except Exception as e:
        await bot.send_message(admin_id, f"⚠️ Ошибка при создании авто-бэкапа: {e}")
