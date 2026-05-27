from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.repository import Database
from bot.keyboards.inline_kb import get_gifts_kb
from utils.achievements import check_achievements

router = Router()

GIFTS = {
    "snack": {"trust": 8, "mood": "happy", "cost": 50, "reply": "А? Вкусняшка? Эм... спасибо. Я как раз проголодался..."},
    "plushie": {"trust": 10, "mood": "happy", "cost": 150, "reply": "Плюшевая игрушка?! Какая милая! ...Т-то есть, неважно. Спасибо."},
    "game": {"trust": 12, "mood": "excited", "cost": 300, "reply": "Ого! Новая игра! Давай поиграем прямо сейчас!"},
    "merch": {"trust": 15, "mood": "excited", "cost": 500, "reply": "Это... лимитированный мерч?! Где ты это достал?! Ты лучший!"},
    "lnovel": {"trust": 9, "mood": "happy", "cost": 100, "reply": "О, ранобэ. Почитаю, когда будет скучно. Спасибо..."}
}

@router.message(F.text.in_(["/gift", "🎁 Подарить"]))
async def cmd_gift(message: Message):
    await message.answer("П-подарки? Мне? Эм... тебе не стоило...", reply_markup=get_gifts_kb())

@router.callback_query(F.data.startswith("gift_"))
async def process_gift(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    gift_type = callback.data.split("_")[1]
    
    user = await db.get_user(user_id)
    gift_info = GIFTS[gift_type]
    
    if user.coins < gift_info["cost"]:
        await callback.message.edit_text(f"У тебя всего {user.coins} 🪙, а это стоит {gift_info['cost']} 🪙! Возвращайся, когда заработаешь больше.")
        await callback.answer()
        return
        
    user.coins -= gift_info["cost"]
    user.trust = min(100, user.trust + gift_info["trust"])
    user.mood = gift_info["mood"]
    await db.update_user(user)
    await db.add_gift(user_id, gift_type)
    
    achievements = await check_achievements(user, db, callback.message)
    if "gift_giver" not in [a.achievement_type for a in await db.get_user_achievements(user_id)]:
        await db.add_achievement(user_id, "gift_giver")
        achievements.append("Gift Giver")
        
    ach_text = f"\n\n🏆 Открыты достижения: {', '.join(achievements)}" if achievements else ""
    
    await callback.message.edit_text(gift_info["reply"] + ach_text)
    await callback.answer()
