from aiogram import Router, F
from aiogram.types import Message
from database.repository import Database
from utils.time_utils import parse_time, format_time_remaining
import time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.fsm.states import RemindStates

router = Router()

@router.message(F.text.in_(["/reminders", "⏰ Мои Напоминания"]))
async def cmd_reminders(message: Message, db: Database):
    reminders = await db.get_user_reminders(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Создать напоминание", callback_data="remind_create")]])
    
    if not reminders:
        await message.answer("У тебя нет никаких напоминаний. И хорошо, мне меньше работы.", reply_markup=kb)
        return
        
    text = "Вот о чём я должна тебе напомнить:\n\n"
    for r in reminders:
        text += f"- {r.text} (через {format_time_remaining(r.fire_at)})\n"
        
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "remind_create")
async def cb_remind_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RemindStates.waiting_for_input)
    await callback.message.edit_text("Отправь мне время и текст. Например: `10m купить снеки` или `2h выпить воды`.")
    await callback.answer()

@router.message(RemindStates.waiting_for_input)
async def process_remind_input(message: Message, state: FSMContext, db: Database):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("Эм... формат должен быть `<время> <текст>`. Например: `10m купить снеки`.")
        return
        
    time_str = parts[0]
    text = parts[1]
    
    fire_at = parse_time(time_str)
    if not fire_at:
        await message.answer("Я не понимаю такой формат времени. Используй что-то вроде 2h, 30m, 1d.")
        return
        
    await db.add_reminder(message.from_user.id, text, fire_at)
    await message.answer(f"Ладно, я напомню тебе '{text}' через {time_str}. Если не забуду.")
    await state.clear()
