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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 минут", callback_data="remind_time_10m"),
         InlineKeyboardButton(text="1 час", callback_data="remind_time_1h")],
        [InlineKeyboardButton(text="1 день", callback_data="remind_time_1d")]
    ])
    await callback.message.edit_text("Выбери, через сколько мне тебе напомнить?", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("remind_time_"))
async def cb_remind_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[2]
    await state.update_data(time_str=time_str)
    await state.set_state(RemindStates.waiting_for_input)
    await callback.message.edit_text(f"Ок. Через {time_str}. А теперь напиши текст напоминания:")
    await callback.answer()

@router.message(RemindStates.waiting_for_input)
async def process_remind_input(message: Message, state: FSMContext, db: Database):
    state_data = await state.get_data()
    time_str = state_data.get("time_str")
    
    if not time_str:
        # Fallback to old format just in case
        parts = message.text.split(" ", 1)
        if len(parts) < 2:
            await message.answer("Пожалуйста, используйте кнопки для выбора времени.")
            return
        time_str = parts[0]
        text = parts[1]
    else:
        text = message.text
    
    fire_at = parse_time(time_str)
    if not fire_at:
        await message.answer("Я не понимаю такой формат времени. Попробуй еще раз.")
        return
        
    await db.add_reminder(message.from_user.id, text, fire_at)
    await message.answer(f"Поняла. Напомню тебе про `{text}`.")
    await state.clear()
