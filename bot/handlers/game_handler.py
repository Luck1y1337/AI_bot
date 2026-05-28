from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.repository import Database
from bot.keyboards.inline_kb import get_quiz_kb
import random
from utils.achievements import ACHIEVEMENTS

router = Router()

QUESTIONS = [
    {"q": "Что превратило меня в девочку?", "opts": ["Магия", "Лекарство", "Проклятие", "Реинкарнация"], "ans": 1},
    {"q": "Как зовут мою младшую сестру?", "opts": ["Михари", "Каэде", "Момидзи", "Асахи"], "ans": 0},
    {"q": "Что я люблю делать больше всего?", "opts": ["Учиться", "Тренироваться", "Играть в игры", "Готовить"], "ans": 2},
    {"q": "Как зовут подругу Михари со средней школы?", "opts": ["Момидзи", "Асахи", "Каэде", "Наюта"], "ans": 2},
    {"q": "Какой мой любимый жанр игр?", "opts": ["Эроге", "Шутеры", "РПГ", "Головоломки"], "ans": 0},
    {"q": "В каком я классе по легенде?", "opts": ["Старшая школа", "Средняя школа", "Колледж", "Младшая школа"], "ans": 1},
    {"q": "Какого цвета у меня волосы?", "opts": ["Блонд", "Черные", "Розовые", "Каштановые"], "ans": 2},
    {"q": "Кто считает меня супер милой?", "opts": ["Все", "Михари", "Момидзи", "Они все"], "ans": 3},
    {"q": "Люблю ли я выходить на улицу?", "opts": ["Да", "Нет", "Иногда", "Только за едой"], "ans": 1},
    {"q": "Как лучше всего провести день?", "opts": ["В школе", "За работой", "Спать и играть", "Шоппинг"], "ans": 2},
    {"q": "Чьей младшей сестрой является Момидзи?", "opts": ["Каэде", "Асахи", "Михари", "У неё нет сестры"], "ans": 0},
    {"q": "Хотел ли я быть девочкой?", "opts": ["Да", "Нет", "Мне всё равно", "Втайне да"], "ans": 1}
]

@router.message(F.text.in_(["/quiz", "🎮 Играть (Quiz)"]))
async def cmd_quiz(message: Message):
    q = random.choice(QUESTIONS)
    await message.answer(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data == "eco_quiz")
async def cb_eco_quiz(callback: CallbackQuery):
    q = random.choice(QUESTIONS)
    await callback.message.edit_text(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data.startswith("quiz_"))
async def process_quiz(callback: CallbackQuery, db: Database):
    is_correct = callback.data.split("_")[1] == "1"
    user = await db.get_user(callback.from_user.id)
    
    if is_correct:
        user.xp += 10
        user.coins += 5
        user.trust = min(100, user.trust + 3)
        await db.update_user(user)
        await callback.message.edit_text("Хмпф. Ты правда ответил правильно. Неплохо. (+10 XP, +5 🪙)")
        
        # Check quiz master
        if user.xp >= 100:
            current_achs = [a.achievement_type for a in await db.get_user_achievements(user.id)]
            if "quiz_master" not in current_achs:
                await db.add_achievement(user.id, "quiz_master")
                await callback.message.answer("🏆 Открыто достижение: Мастер Викторин!")
    else:
        await callback.message.edit_text("Бзззт! Неправильно. Ты вообще меня слушаешь?")
    
    await callback.answer()

@router.message(F.text.in_(["/leaderboard", "🏆 Лидеры"]))
async def cmd_leaderboard(message: Message, db: Database):
    top_users = await db.get_top_users_by_xp(10)
    text = "🏆 **Таблица Лидеров (XP)** 🏆\n\n"
    for i, u in enumerate(top_users):
        inventory = await db.get_user_inventory(u.id)
        titles = [item[3] for item in inventory if item[2] == 'title']
        title_text = f" [{titles[0]}]" if titles else ""
        
        display_name = f"@{u.username}" if u.username else f"ID {u.id}"
        text += f"{i+1}.{title_text} {display_name} - {u.xp} XP\n"
    await message.answer(text)
