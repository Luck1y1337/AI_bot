from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class CryptoStates(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_sell_amount = State()

def get_crypto_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📈 Купить", callback_data="crypto_buy"),
         InlineKeyboardButton(text="📉 Продать", callback_data="crypto_sell")],
        [InlineKeyboardButton(text="🔙 В Банк", callback_data="eco_bank")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_crypto")
async def cb_crypto_market(callback: CallbackQuery, db: Database):
    from utils.levels import get_level
    user = await db.get_user(callback.from_user.id)
    if get_level(user.xp) < 5:
        return await callback.answer("Криптобиржа доступна с 5 уровня!", show_alert=True)
    price_row = await db.get_crypto_price("mahiro_coin")
    if not price_row:
        price = 1000
        await db.update_crypto_price("mahiro_coin", price)
    else:
        price = price_row[0]
        
    user_id = callback.from_user.id
    inv = await db.get_inventory_item(user_id, "crypto_mhr")
    amount = inv[2] if inv else 0
    
    text = "🪙 <b>Криптобиржа Махиро (MHR)</b>\n\n"
    text += f"📈 Текущий курс: <b>{price} 🪙</b> за 1 MHR\n"
    text += f"Курс динамически меняется каждый час.\n\n"
    text += f"Ваш баланс: <b>{amount} MHR</b> (эквивалент {amount * price} 🪙)"
    
    await callback.message.edit_text(text, reply_markup=get_crypto_kb())

@router.callback_query(F.data == "crypto_buy")
async def cb_crypto_buy(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CryptoStates.waiting_for_buy_amount)
    await callback.message.answer("Сколько MHR вы хотите купить? Введите число:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="crypto_cancel")]]))
    await callback.answer()

@router.message(CryptoStates.waiting_for_buy_amount)
async def process_crypto_buy(message: Message, state: FSMContext, db: Database):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except Exception:
        return await message.answer("Пожалуйста, введите корректное положительное число.")
        
    price_row = await db.get_crypto_price("mahiro_coin")
    price = price_row[0] if price_row else 1000
    total_cost = price * amount
    
    if not await db.deduct_coins(message.from_user.id, total_cost):
        await message.answer(f"Недостаточно коинов! Нужно {total_cost} 🪙.")
    else:
        await db.add_inventory_amount(message.from_user.id, "crypto_mhr", amount)
        await message.answer(f"✅ Успешно куплено {amount} MHR за {total_cost} 🪙!")
        
    await state.clear()

@router.callback_query(F.data == "crypto_sell")
async def cb_crypto_sell(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CryptoStates.waiting_for_sell_amount)
    await callback.message.answer("Сколько MHR вы хотите продать? Введите число:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="crypto_cancel")]]))
    await callback.answer()

@router.message(CryptoStates.waiting_for_sell_amount)
async def process_crypto_sell(message: Message, state: FSMContext, db: Database):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except Exception:
        return await message.answer("Пожалуйста, введите корректное положительное число.")
        
    user_id = message.from_user.id
    price_row = await db.get_crypto_price("mahiro_coin")
    price = price_row[0] if price_row else 1000
    total_profit = price * amount
    
    success = await db.remove_inventory_amount(user_id, "crypto_mhr", amount)
    if not success:
        await message.answer("У вас нет столько MHR!")
    else:
        await db.add_coins(user_id, total_profit)
        await message.answer(f"✅ Успешно продано {amount} MHR за {total_profit} 🪙!")
        
    await state.clear()

@router.callback_query(F.data == "crypto_cancel")
async def cb_crypto_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено.")
