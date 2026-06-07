from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.fsm.states import SupportStates
from config.settings import get_settings
from bot.keyboards.main_kb import get_main_menu

router = Router()
settings = get_settings()

@router.message(F.text.in_(["/support", "🆘 Поддержка"]))
async def cmd_support(message: Message, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_ticket)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="support_cancel")]])
    await message.answer("У тебя проблемы? Или просто хочешь поговорить со мной напрямую? Опиши свою проблему в одном сообщении, и я (или кто-то из взрослых) тебе ответим.\n*(Или нажми Отмена)*", reply_markup=kb)

@router.callback_query(F.data == "support_cancel")
async def cb_support_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Обращение в поддержку отменено.")
    await callback.answer()

@router.message(SupportStates.waiting_for_ticket)
async def process_ticket(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("Эм... я не умею читать мысли. Напиши текст.")
        return
        
    if message.text.startswith("/") or message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Режим поддержки отменен.")
        return

    admin_id = settings.ADMIN_USER_IDS[0] if settings.ADMIN_USER_IDS else None
    if not admin_id:
        await message.answer("Похоже, админов нет дома. Попробуй позже.")
        await state.clear()
        return

    text = f"🎫 <b>Новый тикет от {message.from_user.id} (@{message.from_user.username or 'без_юзернейма'}):</b>\n\n{message.text}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"support_reply_{message.from_user.id}")]
    ])
    
    try:
        await bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
        await message.answer("Твоё сообщение отправлено. Жди, пока мы его прочитаем.", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        await message.answer("Произошла ошибка при отправке. Админы спят.")
    
    await state.clear()

from bot.fsm.states import AdminStates

@router.callback_query(F.data.startswith("support_reply_"))
async def cb_support_reply(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_USER_IDS: return
    
    user_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.waiting_for_reply_text)
    await state.update_data(reply_target_id=user_id)
    
    await callback.message.answer(f"Введите текст ответа для пользователя {user_id}:")
    await callback.answer()

@router.message(AdminStates.waiting_for_reply_text)
async def process_admin_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("reply_target_id")
    
    if not user_id:
        await message.answer("Ошибка: ID пользователя потерян.")
        await state.clear()
        return
        
    try:
        await bot.send_message(user_id, f"💌 <b>Ответ от Службы Поддержки (Махиро):</b>\n\n{message.text}", parse_mode="HTML")
        await message.answer("Ответ успешно отправлен пользователю.")
    except Exception as e:
        await message.answer(f"Не удалось отправить ответ: {e}")
        
    await state.clear()
