import asyncio
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, ErrorEvent
from aiogram.utils.text_decorations import html_decoration
from aiogram.exceptions import TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
from bot.handlers import main_handler, admin_handler, game_handler, reminder_handler, gift_handler, support_handler, donate_handler, economy_handler, clan_handler, gacha_handler, pet_handler, raid_handler, market_handler
from media.mood_images import create_placeholders

os.makedirs("logs", exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[
                        # Rotate so logs/mahiro.log never grows without bound (5 MB x 3).
                        RotatingFileHandler("logs/mahiro.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
                        logging.StreamHandler(sys.stdout),
                    ])

logger = logging.getLogger(__name__)

async def on_error(event: ErrorEvent):
    # Catch-all so an exception in any handler is logged and the user gets a
    # soft reply instead of a silent hang.
    update = event.update

    # Benign: a refresh button re-rendered identical content. Telegram rejects
    # the edit, but there's nothing wrong — just ack the click quietly, don't
    # log it as an error or scare the user with a "something went wrong" alert.
    if isinstance(event.exception, TelegramBadRequest) and "message is not modified" in str(event.exception):
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
        return True

    logger.error("Unhandled update error: %s", event.exception, exc_info=event.exception)
    try:
        if update.message:
            await update.message.answer("Ой... что-то пошло не так. Попробуй ещё раз чуть позже.")
        elif update.callback_query:
            await update.callback_query.answer("Ой... что-то пошло не так. Попробуй позже.", show_alert=True)
    except Exception:
        pass
    return True

async def check_reminders(bot: Bot, db: Database):
    reminders = await db.get_due_reminders(time.time())
    for r in reminders:
        try:
            await bot.send_message(r.user_id, f"Uh... hey. You told me to remind you about this:\n{html_decoration.quote(r.text)}")
            await db.delete_reminder(r.id)
        except Exception as e:
            logging.warning(f"Failed to send reminder {r.id} to {r.user_id}: {e}")
            await db.delete_reminder(r.id)

MAX_PROACTIVE_USERS = 20

async def proactive_message(bot: Bot, db: Database, mistral: MistralClient, memory: MemoryManager):
    import random
    users = await db.get_all_users()
    candidates = [u for u in users if u.trust > 40]
    if len(candidates) > MAX_PROACTIVE_USERS:
        candidates = random.sample(candidates, MAX_PROACTIVE_USERS)
    for u in candidates:
        prompt = "It's a random check-in time. Say something in-character."
        sys = build_system_prompt(u.mood, u.trust, [], memory.long.get_user_memory(u.id))
        try:
            resp = await mistral.generate_response(prompt, sys)
            await bot.send_message(u.id, resp)
        except Exception as e:
            logging.debug(f"Proactive message to {u.id} failed: {e}")

async def main():
    settings = get_settings()

    # All persistent state lives next to the DB file, so a single mounted
    # volume (see DB_PATH / Railway Volume) keeps both the DB and long-term memory.
    data_dir = os.path.dirname(settings.DB_PATH) or "."
    logging.info("Database path: %r (directory: %r)", settings.DB_PATH, data_dir)

    # DB_PATH must be a file path, not empty and not a directory. A common
    # misconfig is pointing it at the volume mount dir itself (e.g. /data).
    if not settings.DB_PATH or settings.DB_PATH.endswith(("/", "\\")) or os.path.isdir(settings.DB_PATH):
        logging.critical(
            "DB_PATH=%r is invalid: it must be a FILE path like /data/mahiro.db, "
            "not empty and not a directory.", settings.DB_PATH,
        )
        raise SystemExit(1)

    # Create the data dir and verify it is actually writable — a mounted volume
    # can exist yet be read-only or owned by another user, which surfaces later
    # as an opaque "unable to open database file" from SQLite.
    try:
        os.makedirs(data_dir, exist_ok=True)
        _probe = os.path.join(data_dir, ".write_test")
        with open(_probe, "w") as _f:
            _f.write("ok")
        os.remove(_probe)
    except OSError as e:
        logging.critical(
            "Data directory %r is not writable: %s. On Railway, mount a Volume at "
            "this path and make sure DB_PATH points to a file inside it.", data_dir, e,
        )
        raise SystemExit(1)

    os.makedirs("cache", exist_ok=True)

    create_placeholders()

    bot = Bot(token=settings.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.errors.register(on_error)

    db = Database(settings.DB_PATH)
    await db.connect()

    from seed_cards import seed_cards
    await seed_cards(db)

    mistral = MistralClient(settings.MISTRAL_API_KEY)

    long_term = LongTermMemory(os.path.join(data_dir, "long_term.json"))
    await long_term.load()
    short_term = ShortTermMemory()
    memory = MemoryManager(long_term, short_term)

    from bot.middlewares.maintenance import MaintenanceMiddleware
    
    # Middlewares (applied to both messages and callback queries so bans,
    # whitelist, maintenance and anti-spam cannot be bypassed via inline buttons)
    for mw in (LoggingMiddleware(), MaintenanceMiddleware(), WhitelistMiddleware(), AntiSpamMiddleware()):
        dp.message.middleware(mw)
        dp.callback_query.middleware(mw)

    # Pass dependencies
    deps = {"db": db, "mistral": mistral, "memory": memory}
    
    dp.include_router(admin_handler.router)
    dp.include_router(support_handler.router)
    dp.include_router(game_handler.router)
    dp.include_router(reminder_handler.router)
    dp.include_router(gift_handler.router)
    dp.include_router(donate_handler.router)
    dp.include_router(economy_handler.router)
    dp.include_router(clan_handler.router)
    
    from bot.handlers import inventory_handler, marry_handler, bounty_handler, roulette_pvp_handler, black_market_handler, crypto_handler, rps_handler, trade_handler, customization_handler, dungeon_handler, slots_handler, lottery_handler
    dp.include_router(inventory_handler.router)
    dp.include_router(marry_handler.router)
    dp.include_router(bounty_handler.router)
    dp.include_router(roulette_pvp_handler.router)
    dp.include_router(black_market_handler.router)
    dp.include_router(crypto_handler.router)
    dp.include_router(rps_handler.router)
    dp.include_router(trade_handler.router)
    dp.include_router(customization_handler.router)
    dp.include_router(dungeon_handler.router)
    dp.include_router(slots_handler.router)
    dp.include_router(lottery_handler.router)

    dp.include_router(gacha_handler.router)
    dp.include_router(pet_handler.router)
    dp.include_router(raid_handler.router)
    dp.include_router(market_handler.router)
    
    dp.include_router(main_handler.router)
    
    from bot.handlers import ai_games_handler
    dp.include_router(ai_games_handler.router)

    async def update_crypto_market(db_instance: Database):
        price_row = await db_instance.get_crypto_price("mahiro_coin")
        old_price = price_row[0] if price_row else 1000
        import random
        # Limit crypto price scaling to prevent hyperinflation
        if old_price > 5000:
            multiplier = random.uniform(0.3, 0.9) # High chance to crash if overvalued
        else:
            multiplier = random.uniform(0.5, 2.5) # Reduced max multiplier
            
        new_price = int(old_price * multiplier)
        if new_price < 10: new_price = 10
        if new_price > 10000: new_price = 10000 # Absolute max cap
        await db_instance.update_crypto_price("mahiro_coin", new_price)
        
    async def draw_lottery(bot_inst: Bot, db_inst: Database):
        round_id = await db_inst.get_current_lottery_round()
        total_tickets, total_players = await db_inst.get_lottery_pool(round_id)
        if total_tickets == 0:
            return
        jackpot = total_tickets * 100
        winner_id = await db_inst.draw_lottery_winner(round_id)
        if not winner_id:
            return
        await db_inst.add_coins(winner_id, jackpot)
        await db_inst.add_transaction(0, winner_id, jackpot, "lottery_win")
        try:
            await bot_inst.send_message(winner_id, f"🎉🎟 <b>ВЫ ВЫИГРАЛИ ЛОТЕРЕЮ!</b>\n\nДжекпот: <b>{jackpot} 🪙</b>!\nПоздравляем!")
        except Exception:
            pass
        # Advance to the next round (round number lives in settings, not derived from tickets)
        await db_inst.advance_lottery_round()

    from utils.backup import perform_backup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'interval', seconds=60, args=[bot, db])
    scheduler.add_job(update_crypto_market, 'interval', minutes=60, args=[db])
    scheduler.add_job(proactive_message, 'cron', hour='8,23', args=[bot, db, mistral, memory])
    scheduler.add_job(perform_backup, 'cron', hour='3', minute='0', args=[bot, db])
    scheduler.add_job(draw_lottery, 'cron', day_of_week='sun', hour='20', minute='0', args=[bot, db])
    scheduler.start()

    logging.info("Starting Mahiro bot...")
    try:
        # Public commands — shown to every user.
        user_commands = [
            BotCommand(command="start", description="Разбудить Махиро и начать диалог."),
            BotCommand(command="stats", description="Ваш профиль: сообщения, коины 🪙, XP ✨, доверие, настроение, достижения."),
            BotCommand(command="mood", description="Текущее настроение Махиро и ваш процент доверия."),
            BotCommand(command="reset", description="Стереть краткосрочную память ИИ, если Махиро зависла на теме."),
            BotCommand(command="support", description="Написать тикет администратору (служба поддержки)."),
            BotCommand(command="remind", description="Установить напоминание (например: /remind выпить воды in 10 m)."),
            BotCommand(command="reminders", description="Список ваших активных напоминаний."),
            BotCommand(command="voice", description="Попросить Махиро озвучить ваш текст её голосом."),
            BotCommand(command="quiz", description="Запустить аниме-викторину и заработать XP и коины."),
            BotCommand(command="leaderboard", description="Таблица лидеров (топ по XP)."),
            BotCommand(command="gift", description="Магазин подарков — повышает доверие и настроение."),
            BotCommand(command="donate", description="Пополнить баланс коинов через Telegram Stars."),
            BotCommand(command="promo", description="Активировать промокод на коины и XP."),
        ]
        # Admin-only commands — appended for admins so their menu shows everything.
        admin_commands = user_commands + [
            BotCommand(command="admin", description="Открыть главное меню Админ-Панели."),
            BotCommand(command="addpromo", description="Создать промокод. Пример: /addpromo MAHIRO 100 50 10."),
            BotCommand(command="refund", description="Вернуть донат Stars. Пример: /refund <charge_id>."),
            BotCommand(command="backup", description="Создать бэкап БД сейчас и получить его в личку."),
            BotCommand(command="restore", description="Восстановить БД: ответить командой на файл бэкапа."),
            BotCommand(command="ban", description="Заблокировать пользователя."),
            BotCommand(command="unban", description="Разблокировать пользователя."),
            BotCommand(command="maintenance", description="Включить/выключить режим обслуживания."),
            BotCommand(command="system", description="Нагрузка на сервер (CPU, RAM, Диск)."),
            BotCommand(command="logs", description="Скачать файл логов mahiro.log."),
            BotCommand(command="reload_config", description="Перезагрузить .env без перезапуска бота."),
        ]
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
        for admin_id in settings.ADMIN_USER_IDS:
            try:
                await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            except Exception as e:
                logging.warning(f"Failed to set admin commands for {admin_id}: {e}")

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
