import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config.settings import get_settings
from database.repository import Database
from ai.mistral_client import MistralClient
from ai.prompt_builder import build_system_prompt
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.memory_manager import MemoryManager
from bot.middlewares.antispam import AntiSpamMiddleware
from bot.middlewares.whitelist import WhitelistMiddleware
from bot.middlewares.logging_middleware import LoggingMiddleware
from bot.handlers import main_handler, admin_handler, game_handler, reminder_handler, gift_handler, support_handler, donate_handler
from media.mood_images import create_placeholders
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import threading
from web.app import start_web
import os
import time

os.makedirs("logs", exist_ok=True)

logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[logging.FileHandler("logs/mahiro.log"), logging.StreamHandler()])

async def check_reminders(bot: Bot, db: Database):
    reminders = await db.get_due_reminders(time.time())
    for r in reminders:
        try:
            await bot.send_message(r.user_id, f"Uh... hey. You told me to remind you about this:\n{r.text}")
            await db.delete_reminder(r.id)
        except:
            pass

async def proactive_message(bot: Bot, db: Database, mistral: MistralClient, memory: MemoryManager):
    users = await db.get_all_users()
    for u in users:
        if u.trust > 40:
            prompt = "It's a random check-in time. Say something in-character."
            sys = build_system_prompt(u.mood, u.trust, [], memory.long.get_user_memory(u.id))
            try:
                resp = await mistral.generate_response(prompt, sys)
                await bot.send_message(u.id, resp)
            except:
                pass

async def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("cache", exist_ok=True)
    
    settings = get_settings()
    create_placeholders()

    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()

    db = Database("data/mahiro.db")
    await db.connect()

    mistral = MistralClient(settings.MISTRAL_API_KEY)

    long_term = LongTermMemory()
    await long_term.load()
    short_term = ShortTermMemory()
    memory = MemoryManager(long_term, short_term)

    from bot.middlewares.maintenance import MaintenanceMiddleware
    
    # Middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(MaintenanceMiddleware())
    dp.message.middleware(WhitelistMiddleware())
    dp.message.middleware(AntiSpamMiddleware())

    # Pass dependencies
    deps = {"db": db, "mistral": mistral, "memory": memory}
    
    dp.include_router(admin_handler.router)
    dp.include_router(support_handler.router)
    dp.include_router(game_handler.router)
    dp.include_router(reminder_handler.router)
    dp.include_router(gift_handler.router)
    dp.include_router(donate_handler.router)
    dp.include_router(main_handler.router)

    from utils.backup import perform_backup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'interval', seconds=60, args=[bot, db])
    scheduler.add_job(proactive_message, 'cron', hour='8,23', args=[bot, db, mistral, memory])
    scheduler.add_job(perform_backup, 'cron', hour='3', minute='0', args=[bot])
    scheduler.start()

    # Web App in background
    threading.Thread(target=start_web, daemon=True).start()

    logging.info("Starting Mahiro bot...")
    try:
        commands = [
            BotCommand(command="start", description="Разбудить Махиро"),
            BotCommand(command="stats", description="Показать мою статистику"),
            BotCommand(command="mood", description="Узнать настроение Махиро"),
            BotCommand(command="reset", description="Сбросить контекст диалога"),
            BotCommand(command="voice", description="Озвучить текст голосом"),
            BotCommand(command="quiz", description="Начать аниме-викторину"),
            BotCommand(command="leaderboard", description="Таблица лидеров (Топ XP)"),
            BotCommand(command="gift", description="Магазин подарков"),
            BotCommand(command="donate", description="Пополнить баланс коинов"),
            BotCommand(command="reminders", description="Список моих напоминаний"),
            BotCommand(command="support", description="Написать в службу поддержки"),
            BotCommand(command="admin", description="👑 Админ-Панель (только для админов)"),
        ]
        await bot.set_my_commands(commands)
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, **deps)
    finally:
        await db.close()
        await mistral.close()
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped gracefully.")
