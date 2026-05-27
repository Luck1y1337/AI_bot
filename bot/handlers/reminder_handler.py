from aiogram import Router, F
from aiogram.types import Message
from database.repository import Database
from utils.time_utils import parse_time, format_time_remaining
import time

router = Router()

@router.message(F.text.startswith("/remind "))
async def cmd_remind(message: Message, db: Database):
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("Эм... формат должен быть `/remind <время> <текст>`. Например: `/remind 10m купить снеки`.")
        return
        
    time_str = parts[1]
    text = parts[2]
    
    fire_at = parse_time(time_str)
    if not fire_at:
        await message.answer("Я не понимаю такой формат времени. Используй что-то вроде 2h, 30m, 1d.")
        return
        
    await db.add_reminder(message.from_user.id, text, fire_at)
    await message.answer(f"Ладно, я напомню тебе '{text}' через {time_str}. Если не забуду.")

@router.message(F.text.in_(["/reminders", "⏰ Мои Напоминания"]))
async def cmd_reminders(message: Message, db: Database):
    reminders = await db.get_user_reminders(message.from_user.id)
    if not reminders:
        await message.answer("У тебя нет никаких напоминаний. И хорошо, мне меньше работы.")
        return
        
    text = "Вот о чём я должна тебе напомнить:\n\n"
    for r in reminders:
        text += f"- {r.text} (через {format_time_remaining(r.fire_at)})\n"
        
    await message.answer(text)
