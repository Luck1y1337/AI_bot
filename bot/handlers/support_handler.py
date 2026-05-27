from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.fsm.states import SupportStates
from config.settings import get_settings
from bot.keyboards.main_kb import get_main_menu

router = Router()
settings = get_settings()

@router.message(F.text.in_(["/support", "🆘 Поддержка"]))
async def cmd_support(message: Message, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_ticket)
    await message.answer("У тебя проблемы? Или просто хочешь поговорить со мной напрямую? Опиши свою проблему в одном сообщении, и я (или кто-то из взрослых) тебе ответим.")

@router.message(SupportStates.waiting_for_ticket)
async def process_ticket(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("Эм... я не умею читать мысли. Напиши текст.")
        return

    admin_id = settings.ADMIN_USER_IDS[0] if settings.ADMIN_USER_IDS else None
    if not admin_id:
        await message.answer("Похоже, админов нет дома. Попробуй позже.")
        await state.clear()
        return

    text = f"🎫 **Новый тикет от {message.from_user.id} (@{message.from_user.username or 'без_юзернейма'}):**\n\n{message.text}\n\n*Для ответа используйте команду /reply {message.from_user.id} <ваш ответ>*"
    try:
        await bot.send_message(admin_id, text)
        await message.answer("Твоё сообщение отправлено. Жди, пока мы его прочитаем.", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        await message.answer("Произошла ошибка при отправке. Админы спят.")
    
    await state.clear()

@router.message(F.text.startswith("/reply "))
async def cmd_reply(message: Message, bot: Bot):
    if message.from_user.id not in settings.ADMIN_USER_IDS:
        return
    
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("Использование: /reply <user_id> <текст ответа>")
        return
        
    user_id = parts[1]
    reply_text = parts[2]
    
    try:
        await bot.send_message(user_id, f"💌 **Ответ от Службы Поддержки (Махиро):**\n\n{reply_text}")
        await message.answer("Ответ успешно отправлен пользователю.")
    except Exception as e:
        await message.answer(f"Не удалось отправить ответ: {e}")
