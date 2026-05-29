from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from database.repository import Database
from ai.mistral_client import MistralClient
from ai.prompt_builder import build_system_prompt
from memory.memory_manager import MemoryManager
from media.tts import generate_tts
from media.charts import generate_activity_chart, generate_trust_chart
from utils.triggers import analyze_triggers
from ai.triggers import TriggerSystem
from utils.achievements import check_achievements
from bot.keyboards.main_kb import get_main_menu, get_pay_users_kb
from aiogram.fsm.context import FSMContext
from bot.fsm.states import PayStates
from aiogram.types import CallbackQuery
import random
import os

router = Router()
old_trigger_system = TriggerSystem()

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if user.username != (message.from_user.username or ""):
        user.username = message.from_user.username or ""
        await db.update_user(user)
        
    if user.message_count == 0:
        from utils.admin_alerts import notify_admins
        await notify_admins(bot, f"Новый пользователь начал использовать бота: {message.from_user.id} (@{message.from_user.username})")
    await message.answer("Эм... привет. Я Махиро. А ты кто?", reply_markup=get_main_menu(message.from_user.id))
    
@router.message(F.text.in_(["/stats", "📊 Моя Статистика"]))
async def cmd_stats(message: Message, db: Database):
    user = await db.get_user(message.from_user.id)
    achievements = await db.get_user_achievements(message.from_user.id)
    inventory = await db.get_user_inventory(message.from_user.id)
    
    # Beautify achievements
    ach_text = "\n".join([f"🏆 {a.achievement_type}" for a in achievements]) if achievements else "Пока нет 😔"
    
    # Find Title
    titles = [item[3] for item in inventory if item[2] == 'title']
    title_text = f" [{titles[0]}]" if titles else ""
    
    text = (f"**Твоя Статистика**{title_text}\n"
            f"Сообщений: {user.message_count}\n"
            f"Доверие: {user.trust}%\n"
            f"Настроение: {user.mood}\n"
            f"XP: {user.xp} ✨\n"
            f"MahiroCoins: 🪙 {user.coins}\n\n"
            f"**Достижения:**\n{ach_text}")
    await message.answer(text)



@router.message(F.text.in_(["/reset"]))
async def cmd_reset(message: Message, memory: MemoryManager):
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
async def btn_voice_help(message: Message):
    await message.answer("Напиши `/voice [свой текст]`, чтобы я сказала это вслух!")

@router.message(F.text.startswith("/voice "))
async def cmd_voice(message: Message, db: Database, mistral: MistralClient, memory: MemoryManager):
    text = message.text.replace("/voice ", "")
    user = await db.get_user(message.from_user.id)
    
    # Fetch modifier
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'prompt_modifier'") as cursor:
        row = await cursor.fetchone()
    modifier = row[0] if row else ""
    
    # Process like normal message
    sys_prompt = build_system_prompt(user.mood, user.trust, memory.short.get_history(user.id), memory.long.get_user_memory(user.id), modifier)
    response = await mistral.generate_response(text, sys_prompt)
    
    # Generate TTS
    ogg_path = await generate_tts(response)
    await message.answer_voice(FSInputFile(ogg_path))

@router.message(F.photo)
async def process_photo(message: Message, db: Database, mistral: MistralClient, bot: Bot, memory: MemoryManager):
    user = await db.get_user(message.from_user.id)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    
    desc = await mistral.analyze_image(url)
    user_prompt = f"Отреагируй на эту картинку, которую я тебе отправил. Вот что ты видишь: {desc}"
    
    # Memory update
    memory.short.add_message(user.id, "user", "[Sent an image]")
    
    # Fetch modifier
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'prompt_modifier'") as cursor:
        row = await cursor.fetchone()
    modifier = row[0] if row else ""
    
    sys_prompt = build_system_prompt(user.mood, user.trust, memory.short.get_history(user.id), memory.long.get_user_memory(user.id), modifier)
    response = await mistral.generate_response(user_prompt, sys_prompt)
    
    memory.short.add_message(user.id, "assistant", response)
    
    await message.answer(response)

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
        await message.answer(fast_response, reply_markup=get_main_menu(user_id))
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
    response = await mistral.generate_response(text, sys_prompt)
    memory.short.add_message(user_id, "assistant", response)
    
    await db.process_contract_action(user_id, "send_messages", 1)
    
    # Achievements
    achievements = await check_achievements(user, db, message)
    ach_text = f"\n\n🏆 Открыты достижения: {', '.join(achievements)}" if achievements else ""
    
    # Send mood image occasionally
    if random.random() < 0.2:
        img_path = f"media/images/{user.mood}.png"
        if os.path.exists(img_path):
            await message.answer_photo(FSInputFile(img_path), caption=response + ach_text, reply_markup=get_main_menu(user_id))
            return
            
    await message.answer(response + ach_text, reply_markup=get_main_menu(user_id))
