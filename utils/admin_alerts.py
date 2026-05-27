import logging
from aiogram import Bot
from config.settings import get_settings

async def notify_admins(bot: Bot, message: str):
    settings = get_settings()
    for admin_id in settings.ADMIN_USER_IDS:
        try:
            await bot.send_message(admin_id, f"⚠️ **Admin Alert** ⚠️\n\n{message}")
        except Exception as e:
            logging.error(f"Failed to send admin alert to {admin_id}: {e}")
