from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class TradeStates(StatesGroup):
    waiting_for_amount = State()

# In-memory trades
# { "trade_id": { "from": user_id, "to": target_id, "item": "wood", "amount": 10, "status": "pending" } }
ACTIVE_TRADES = {}

def get_trade_confirm_kb(trade_id: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"trade_accept_{trade_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"trade_decline_{trade_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_trade")
async def cb_trade_menu(callback: CallbackQuery, db: Database, state: FSMContext):
    from bot.keyboards.main_kb import get_social_users_kb
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    
    if not users:
        return await callback.answer("Нет доступных игроков для трейда.", show_alert=True)
        
    await state.set_state(TradeStates.waiting_for_amount)
    await state.update_data(trade_step="select_user")
    await callback.message.edit_text("🤝 **Прямой Обмен (Трейд)**\n\nВыберите игрока, которому хотите передать ресурсы:", reply_markup=get_social_users_kb(users, 0))

@router.callback_query(TradeStates.waiting_for_amount, F.data.startswith("pay_select_"))
async def cb_trade_select_user(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    if data.get("trade_step") != "select_user": return
    
    target_id = int(callback.data.split("_")[2])
    await state.update_data(trade_target=target_id, trade_step="select_item")
    
    # Show items
    user_id = callback.from_user.id
    items = []
    async with db._conn.execute('SELECT item_type, amount FROM inventory WHERE user_id = ?', (user_id,)) as cursor:
        items = await cursor.fetchall()
        
    kb = []
    for itype, amount in items:
        if amount > 0:
            kb.append([InlineKeyboardButton(text=f"{itype} ({amount} шт)", callback_data=f"trade_item_{itype}")])
            
    kb.append([InlineKeyboardButton(text="Отмена", callback_data="trade_cancel")])
    
    await callback.message.edit_text(f"Выбран игрок {target_id}. Что вы хотите ему передать?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(TradeStates.waiting_for_amount, F.data.startswith("trade_item_"))
async def cb_trade_select_item(callback: CallbackQuery, state: FSMContext):
    item_type = callback.data.replace("trade_item_", "")
    await state.update_data(trade_item=item_type, trade_step="enter_amount")
    
    await callback.message.edit_text(f"Выбран предмет: {item_type}. Напишите количество для передачи:")
    
@router.message(TradeStates.waiting_for_amount)
async def process_trade_amount(message: Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    if data.get("trade_step") != "enter_amount": return
    
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        return await message.answer("Пожалуйста, введите корректное положительное число.")
        
    target_id = data.get("trade_target")
    item_type = data.get("trade_item")
    user_id = message.from_user.id
    
    inv = await db.get_inventory_item(user_id, item_type)
    if not inv or inv[2] < amount:
        await message.answer("У вас нет такого количества!")
        await state.clear()
        return
        
    import random
    trade_id = str(random.randint(10000, 99999))
    ACTIVE_TRADES[trade_id] = {
        "from": user_id,
        "to": target_id,
        "item": item_type,
        "amount": amount,
        "status": "pending"
    }
    
    await message.answer(f"Трейд #{trade_id} отправлен игроку {target_id}. Ожидаем подтверждения...")
    
    try:
        await bot.send_message(
            target_id, 
            f"🤝 **Входящий Трейд!**\n\nИгрок {user_id} хочет передать вам:\nПредмет: {item_type}\nКоличество: {amount} шт.\n\nПринять?",
            reply_markup=get_trade_confirm_kb(trade_id)
        )
    except: pass
    
    await state.clear()

@router.callback_query(F.data.startswith("trade_accept_"))
async def cb_trade_accept(callback: CallbackQuery, db: Database, bot: Bot):
    trade_id = callback.data.split("_")[2]
    if trade_id not in ACTIVE_TRADES:
        return await callback.message.edit_text("Трейд не найден или уже завершен.")
        
    trade = ACTIVE_TRADES[trade_id]
    if trade["status"] != "pending":
        return await callback.message.edit_text("Трейд уже обработан.")
        
    if trade["to"] != callback.from_user.id:
        return await callback.answer("Это не вам!", show_alert=True)
        
    # Process
    success = await db.remove_inventory_amount(trade["from"], trade["item"], trade["amount"])
    if not success:
        trade["status"] = "failed"
        await callback.message.edit_text("У отправителя больше нет этих предметов!")
        try: await bot.send_message(trade["from"], f"Трейд #{trade_id} отменен: у вас не хватило предметов.")
        except: pass
        return
        
    await db.add_inventory_amount(trade["to"], trade["item"], trade["amount"])
    trade["status"] = "completed"
    
    await callback.message.edit_text(f"✅ Вы успешно получили {trade['amount']}x {trade['item']} от {trade['from']}!")
    try: await bot.send_message(trade["from"], f"✅ Трейд #{trade_id} завершен! Игрок {trade['to']} принял вещи.")
    except: pass
    del ACTIVE_TRADES[trade_id]

@router.callback_query(F.data.startswith("trade_decline_"))
async def cb_trade_decline(callback: CallbackQuery, bot: Bot):
    trade_id = callback.data.split("_")[2]
    if trade_id not in ACTIVE_TRADES:
        return await callback.message.edit_text("Трейд не найден.")
        
    trade = ACTIVE_TRADES[trade_id]
    trade["status"] = "declined"
    
    await callback.message.edit_text("❌ Вы отклонили трейд.")
    try: await bot.send_message(trade["from"], f"❌ Игрок {trade['to']} отклонил трейд #{trade_id}.")
    except: pass
    del ACTIVE_TRADES[trade_id]

@router.callback_query(F.data == "trade_cancel")
async def cb_trade_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено.")
