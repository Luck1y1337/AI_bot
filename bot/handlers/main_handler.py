from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.text_decorations import html_decoration
from database.repository import Database
from ai.mistral_client import MistralClient
from ai.prompt_builder import build_system_prompt
from memory.memory_manager import MemoryManager
from media.tts import generate_tts
from config.settings import get_settings
from bot.fsm.states import VoiceStates, PromoStates
from utils.triggers import analyze_triggers
from ai.triggers import TriggerSystem
from utils.achievements import check_achievements
from utils.levels import get_level, get_title, get_xp_for_next, check_level_up
from bot.keyboards.main_kb import get_main_menu, get_main_hub, HUB_HEADER
from utils.profile_gen import generate_profile_image
import random
import os
import io

router = Router()
old_trigger_system = TriggerSystem()

@router.message(F.text.lower().in_(["отмена", "/cancel", "🔙 назад", "назад"]), ~StateFilter(None))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu(message.from_user.id))

REFERRAL_BONUS = 500

# --- Main inline hub ---
@router.message(F.text.in_(["/menu", "☰ Меню"]))
async def cmd_menu(message: Message):
    await message.answer(HUB_HEADER, reply_markup=get_main_hub(message.from_user.id))

@router.callback_query(F.data.in_(["main_hub", "menu_main"]))
async def cb_main_hub(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(HUB_HEADER, reply_markup=get_main_hub(callback.from_user.id))
    except Exception:
        # e.g. previous message was a photo (caption) — send a fresh hub instead.
        await callback.message.answer(HUB_HEADER, reply_markup=get_main_hub(callback.from_user.id))
    await callback.answer()

@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: Message, db: Database, bot: Bot, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user.username != (message.from_user.username or ""):
        user.username = message.from_user.username or ""
        await db.update_user(user)

    if user.message_count == 0:
        from utils.admin_alerts import notify_admins
        await notify_admins(bot, f"Новый пользователь начал использовать бота: {message.from_user.id} (@{message.from_user.username})")

    if not user.tutorial_done:
        await db.add_coins(user.id, 500)
        await db.complete_tutorial(user.id)

        # Referral: /start ref_12345
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1].replace("ref_", ""))
                if referrer_id != message.from_user.id:
                    user.referred_by = referrer_id
                    await db.update_user(user)
                    await db.add_coins(referrer_id, REFERRAL_BONUS)
                    await db.add_coins(user.id, REFERRAL_BONUS)
                    try:
                        await bot.send_message(referrer_id, f"🎉 Ваш друг присоединился по вашей ссылке! Вам начислено <b>{REFERRAL_BONUS} 🪙</b>!")
                    except Exception: pass
            except (ValueError, TypeError): pass

        tutorial_text = (
            "О, новенький! Добро пожаловать. Я Махиро. 🎀\n\n"
            "Давай я покажу тебе, как тут всё устроено. Я перевела тебе твой первый стартовый капитал: <b>500 🪙</b>!\n\n"
            "🎯 <b>Твой первый квест:</b>\n"
            "Открой «☰ Меню» → <b>💼 Заработок</b> → <b>🏪 Магазин</b> и купи себе энергетик!"
        )
        await message.answer(tutorial_text, reply_markup=get_main_menu(message.from_user.id))
        await message.answer(HUB_HEADER, reply_markup=get_main_hub(message.from_user.id))
    else:
        await message.answer("Эм... привет. Я Махиро. 🎀", reply_markup=get_main_menu(message.from_user.id))
        await message.answer(HUB_HEADER, reply_markup=get_main_hub(message.from_user.id))
    
@router.message(F.text.in_(["/stats", "📊 Моя Статистика"]))
async def cmd_stats(message: Message, db: Database, bot: Bot):
    await _show_stats(message, message.from_user.id, db, bot)

@router.callback_query(F.data == "open_stats")
async def cb_open_stats(callback: CallbackQuery, db: Database, bot: Bot):
    await _show_stats(callback.message, callback.from_user.id, db, bot)
    await callback.answer()

async def _show_stats(chat: Message, user_id: int, db: Database, bot: Bot):
    message = chat  # kept name below for minimal diff
    user = await db.get_user(user_id)
    achievements = await db.get_user_achievements(user_id)
    inventory = await db.get_user_inventory(user_id)

    # Beautify achievements
    ach_text = "\n".join([f"🏆 {a.achievement_type}" for a in achievements]) if achievements else "Пока нет 😔"
    
    # Find Title
    titles = [item[3] for item in inventory if item[2] == 'title']
    title_text = f" [{titles[0]}]" if titles else ""
    
    from utils.formatting import generate_progress_bar
    level = get_level(user.xp)
    xp_cur, xp_need = get_xp_for_next(user.xp)
    xp_bar = generate_progress_bar(xp_cur, xp_need, length=10)
    rank_title = get_title(user.xp)
    streak_text = f"🔥 Streak: {user.streak_count} дн." if user.streak_count > 1 else ""

    text = (f"<b>Твоя Статистика</b>{title_text}\n"
            f"📊 Уровень: <b>{level}</b> — {rank_title}\n"
            f"✨ XP: {xp_bar} {xp_cur}/{xp_need}\n"
            f"🪙 MahiroCoins: {user.coins}\n"
            f"💬 Сообщений: {user.message_count}\n"
            f"💕 Доверие: {user.trust}%\n"
            f"😊 Настроение: {user.mood}\n"
            f"{streak_text}\n\n"
            f"<b>Достижения:</b>\n{ach_text}").strip()
            
    # Generate profile image
    avatar_bytes = None
    try:
        user_photos = await bot.get_user_profile_photos(user_id)
        if user_photos.total_count > 0:
            photo = user_photos.photos[0][-1]
            file = await bot.get_file(photo.file_id)
            io_stream = io.BytesIO()
            await bot.download_file(file.file_path, io_stream)
            avatar_bytes = io_stream.getvalue()
    except Exception:
        pass
        
    image_io = await generate_profile_image(user, avatar_bytes, frame=user.profile_frame)
    from bot.keyboards.main_kb import get_stats_kb
    await message.answer_photo(BufferedInputFile(image_io.getvalue(), "profile.png"), caption=text, reply_markup=get_stats_kb())



@router.callback_query(F.data == "stats_reset")
async def cb_stats_reset(callback: CallbackQuery, memory):
    memory.short.clear_history(callback.from_user.id)
    await callback.answer("🔄 Память ИИ успешно сброшена!", show_alert=True)

@router.callback_query(F.data == "stats_reminders")
async def cb_stats_reminders(callback: CallbackQuery, db: Database):
    reminders = await db.get_user_reminders(callback.from_user.id)
    if not reminders:
        text = "⏰ У вас нет активных напоминаний.\n\n<i>Вы можете создать их с помощью команды /remind</i>"
    else:
        text = "⏰ <b>Ваши активные напоминания:</b>\n\n"
        from datetime import datetime
        for r in reminders:
            dt = datetime.fromtimestamp(r.fire_at).strftime('%Y-%m-%d %H:%M')
            text += f"• {html_decoration.quote(r.text)} (до {dt})\n"
    
    await callback.message.answer(text)
    await callback.answer()

@router.message(F.text.in_(["/reset"]))
async def cmd_reset(message: Message, memory):
    memory.short.clear_history(message.from_user.id)
    await message.answer("Хм… начнём сначала? 😅\n(история диалога очищена)")

@router.message(F.text.in_(["/mood"]))
async def cmd_mood(message: Message, db: Database):
    user = await db.get_user(message.from_user.id)
    mood_emojis = {
        "normal": "😐",
        "happy": "😊",
        "annoyed": "😤",
        "tired": "😮‍💨",
        "sleepy": "😴",
        "excited": "😳",
        "sad": "😔"
    }
    emoji = mood_emojis.get(user.mood, "😐")
    response = f"Эм… сейчас я {user.mood} {emoji}\nМы общаемся уже какое-то время… доверие: {user.trust}%"
    await message.answer(response)

@router.message(F.text == "🎤 Голос")
async def btn_voice_help(message: Message, state: FSMContext):
    await _start_voice(message, state)

@router.callback_query(F.data == "open_voice")
async def cb_open_voice(callback: CallbackQuery, state: FSMContext):
    await _start_voice(callback.message, state)
    await callback.answer()

async def _start_voice(chat: Message, state: FSMContext):
    await state.set_state(VoiceStates.waiting_for_text)
    await chat.answer("🎤 <b>Озвучка</b>\nОтправь текст, который я произнесу своим голосом:")

@router.message(VoiceStates.waiting_for_text)
async def process_voice_text(message: Message, state: FSMContext, db: Database, mistral: MistralClient, memory: MemoryManager):
    text = message.text
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    # Fetch modifier
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'prompt_modifier'") as cursor:
        row = await cursor.fetchone()
    modifier = row[0] if row else ""
    
    # Process like normal message
    sys_prompt = build_system_prompt(user.mood, user.trust, memory.short.get_history(user.id), memory.long.get_user_memory(user.id), modifier)
    response = await mistral.generate_response(text, sys_prompt, memory.short.get_history(user.id))
    
    # Generate TTS
    ogg_path = await generate_tts(response)
    await message.answer_voice(FSInputFile(ogg_path))

@router.message(F.photo)
async def process_photo(message: Message, db: Database, mistral: MistralClient, bot: Bot, memory: MemoryManager):
    user = await db.get_user(message.from_user.id)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = io.BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    import base64
    b64_image = base64.b64encode(file_bytes.getvalue()).decode()
    data_url = f"data:image/jpeg;base64,{b64_image}"

    desc = await mistral.analyze_image(data_url)
    user_prompt = f"Отреагируй на эту картинку, которую я тебе отправил. Вот что ты видишь: {desc}"
    
    # Memory update
    memory.short.add_message(user.id, "user", "[Sent an image]")
    
    # Fetch modifier
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'prompt_modifier'") as cursor:
        row = await cursor.fetchone()
    modifier = row[0] if row else ""
    
    sys_prompt = build_system_prompt(user.mood, user.trust, memory.short.get_history(user.id), memory.long.get_user_memory(user.id), modifier)
    response = await mistral.generate_response(user_prompt, sys_prompt, memory.short.get_history(user.id))
    
    memory.short.add_message(user.id, "assistant", response)

    # AI output is free text — escape so stray <, >, & don't break HTML parsing.
    await message.answer(html_decoration.quote(response))

@router.message(F.text == "🎁 Промокод")
async def btn_promo_start(message: Message, state: FSMContext):
    await _start_promo(message, state)

@router.callback_query(F.data == "open_promo")
async def cb_open_promo(callback: CallbackQuery, state: FSMContext):
    await _start_promo(callback.message, state)
    await callback.answer()

async def _start_promo(chat: Message, state: FSMContext):
    await state.set_state(PromoStates.waiting_for_code)
    await chat.answer("🎁 <b>Промокод</b>\nОтправь мне код:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_promo")]]))

@router.callback_query(F.data == "cancel_promo")
async def cancel_promo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Ввод промокода отменен.")

@router.message(PromoStates.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext, db: Database):
    code = message.text.strip()
    
    async with db._conn.execute('SELECT reward_coins, reward_xp, max_uses, current_uses FROM promocodes WHERE code = ?', (code,)) as cursor:
        row = await cursor.fetchone()
        
    if not row:
        await message.answer("Этот промокод не существует или введен неверно.")
        await state.clear()
        return
        
    coins, xp, max_uses, current_uses = row
    if current_uses >= max_uses:
        await message.answer("Этот промокод уже закончился! :(")
        await state.clear()
        return
        
    # Check if user already used this promo
    action_str = f"promo_{code}"
    async with db._conn.execute('SELECT id FROM transactions WHERE sender_id = ? AND action_type = ?', (message.from_user.id, action_str)) as cursor:
        used = await cursor.fetchone()
        
    if used:
        await message.answer("Вы уже активировали этот промокод ранее!")
        await state.clear()
        return
        
    # Give reward
    user = await db.get_user(message.from_user.id)
    user.coins += coins
    user.xp += xp
    await db.update_user(user)
    
    # Increment uses
    await db._conn.execute('UPDATE promocodes SET current_uses = current_uses + 1 WHERE code = ?', (code,))
    await db.add_transaction(message.from_user.id, 0, coins, action_str)
    await db._conn.commit()
    
    await message.answer(f"🎉 Промокод активирован! Ты получил {coins} 🪙 и {xp} ✨ XP.")
    await state.clear()

@router.message(F.text == "/invite")
async def cmd_invite(message: Message, db: Database, bot: Bot):
    await _show_invite(message, message.from_user.id, db, bot)

@router.callback_query(F.data == "open_invite")
async def cb_open_invite(callback: CallbackQuery, db: Database, bot: Bot):
    await _show_invite(callback.message, callback.from_user.id, db, bot)
    await callback.answer()

async def _show_invite(chat: Message, user_id: int, db: Database, bot: Bot):
    bot_user = await bot.me()
    ref_link = f"https://t.me/{bot_user.username}?start=ref_{user_id}"
    ref_count = await db.get_referral_count(user_id)
    text = (
        f"🔗 <b>Твоя реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"Поделись ссылкой с друзьями — вы оба получите <b>{REFERRAL_BONUS} 🪙</b>!\n\n"
        f"👥 Приглашено друзей: <b>{ref_count}</b>"
    )
    await chat.answer(text)

@router.message(F.text)
async def process_message(message: Message, db: Database, mistral: MistralClient, memory: MemoryManager, bot: Bot):
    user_id = message.from_user.id
    text = message.text
    
    if message.chat.type in ['group', 'supergroup']:
        bot_user = await bot.me()
        is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_user.id
        is_mention = text and ("махиро" in text.lower() or f"@{bot_user.username}" in text)
        is_random = random.random() < 0.02
        
        if not (is_reply or is_mention or is_random):
            return
            
    user = await db.get_user(user_id)
    if user.username != (message.from_user.username or ""):
        user.username = message.from_user.username or ""
        
    if user.is_banned:
        return
        
    user.message_count += 1
    user.coins += 1  # Reward 1 coin per message
    
    # Base XP with pet buff
    earned_xp = random.randint(2, 5)
    inventory = await db.get_user_inventory(user.id)
    has_slime = any(i[2] == "pet" and i[3] == "Слайм-Помощник" for i in inventory)
    if has_slime:
        earned_xp = int(earned_xp * 1.2)
    old_xp = user.xp
    user.xp += earned_xp
    
    # Analyze triggers
    trust_delta, mood_force, triggers = analyze_triggers(text)
    user.trust = max(0, min(100, user.trust + trust_delta))
    
    if mood_force:
        user.mood = mood_force
    elif random.random() < 0.3:
        moods = ["normal", "happy", "annoyed", "tired", "sleepy", "excited", "sad"]
        user.mood = random.choice(moods)
        
    # Analyze old triggers
    fast_response = old_trigger_system.check_triggers(text, user.trust / 100)
    if fast_response:
        await message.answer(html_decoration.quote(fast_response), reply_markup=get_main_menu(user_id))
        memory.short.add_message(user_id, "user", text)
        memory.short.add_message(user_id, "assistant", fast_response)
        await db.update_user(user)
        return
        
    # Memory
    await memory.extract_and_update(user_id, text)
    memory.short.add_message(user_id, "user", text)
    
    # Fetch modifier
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'prompt_modifier'") as cursor:
        row = await cursor.fetchone()
    modifier = row[0] if row else ""
    
    sys_prompt = build_system_prompt(user.mood, user.trust, memory.short.get_history(user_id), memory.long.get_user_memory(user_id), modifier, user.custom_prompt)
    response = await mistral.generate_response(text, sys_prompt, memory.short.get_history(user_id))
    memory.short.add_message(user_id, "assistant", response)
    
    await db.process_contract_action(user_id, "send_messages", 1)
    
    # Level up check
    leveled_up, new_level, level_reward = check_level_up(old_xp, user.xp)
    level_text = ""
    if leveled_up:
        user.coins += level_reward
        new_title = get_title(user.xp)
        level_text = f"\n\n🎉 <b>Уровень {new_level}!</b> (+{level_reward} 🪙) — {new_title}"

    # Achievements
    achievements = await check_achievements(user, db, message)
    ach_text = f"\n\n🏆 Открыты достижения: {', '.join(achievements)}" if achievements else ""
    
    # Send mood image occasionally
    if random.random() < 0.2:
        img_path = f"media/images/{user.mood}.png"
        if os.path.exists(img_path):
            await message.answer_photo(FSInputFile(img_path), caption=html_decoration.quote(response) + level_text + ach_text, reply_markup=get_main_menu(user_id))
            return

    await message.answer(html_decoration.quote(response) + level_text + ach_text, reply_markup=get_main_menu(user_id))
