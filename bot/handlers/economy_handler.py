from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from database.repository import Database
from bot.fsm.states import PayStates, CasinoStates
from aiogram.fsm.context import FSMContext
from bot.keyboards.main_kb import get_pay_users_kb, get_economy_menu
from bot.keyboards.economy_kb import get_businesses_kb, get_shop_kb, get_bank_kb
import time
import random

router = Router()

@router.message(F.text == "🌟 Интерактив и Экономика")
async def cmd_economy_menu(message: Message):
    await message.answer("Добро пожаловать в раздел Игр и Экономики! Выберите действие:", reply_markup=get_economy_menu())

# --- Ежедневный Бонус ---
@router.callback_query(F.data == "eco_daily")
async def cb_eco_daily(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    now = time.time()
    if now - user.last_daily_time >= 86400:
        user.coins += 50
        user.xp += 10
        user.last_daily_time = now
        await db.update_user(user)
        await db.add_transaction(0, user.id, 50, "daily_bonus")
        await callback.message.edit_text("Ура! Ты получил(а) ежедневный бонус:\n🪙 50 MahiroCoins\n✨ 10 XP\n\nПриходи завтра!", reply_markup=get_economy_menu())
    else:
        left = int(86400 - (now - user.last_daily_time))
        hours = left // 3600
        mins = (left % 3600) // 60
        await callback.answer(f"Бонус будет доступен через {hours} ч. {mins} мин.", show_alert=True)

# --- Гача ---
@router.callback_query(F.data == "eco_gacha")
async def cb_eco_gacha(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    cost = 20
    if user.coins < cost:
        await callback.answer(f"Недостаточно коинов. Нужно {cost} 🪙.", show_alert=True)
        return
        
    user.coins -= cost
    roll = random.random()
    if roll < 0.05:
        user.coins += 200
        reward = "ОГО! ЗОЛОТАЯ ФИГУРКА АНИМЕ! Вы продаете её за 200 🪙!"
    elif roll < 0.3:
        user.coins += 50
        reward = "Неплохо, редкий стикерпак. Стоит 50 🪙."
    else:
        user.coins += 10
        reward = "Упс, почти пусто. Но ты нашел 10 🪙 на дне коробки."
        
    await db.update_user(user)
    await db.add_transaction(user.id, 0, cost, "gacha_roll")
    await callback.message.edit_text(f"🎰 **Крутим Гачу...**\n\n{reward}\n\nТвой баланс: {user.coins} 🪙", reply_markup=get_economy_menu())

# --- Перевод Коинов ---
@router.callback_query(F.data == "eco_transfer")
async def cb_eco_transfer(callback: CallbackQuery, db: Database, state: FSMContext):
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    if not users:
        await callback.answer("Нет других пользователей.", show_alert=True)
        return
    await state.set_state(PayStates.waiting_for_user)
    await callback.message.edit_text("Кому перевести коины?", reply_markup=get_pay_users_kb(users, 0))

@router.callback_query(F.data.startswith("pay_page_"))
async def pay_paginate(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    await callback.message.edit_reply_markup(reply_markup=get_pay_users_kb(users, page))
    await callback.answer()

@router.callback_query(F.data == "pay_cancel")
async def pay_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добро пожаловать в раздел Игр и Экономики! Выберите действие:", reply_markup=get_economy_menu())
    await callback.answer("Перевод отменен.")

@router.callback_query(F.data.startswith("pay_select_"))
async def pay_select(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    await state.update_data(pay_target_id=target_id)
    await state.set_state(PayStates.waiting_for_amount)
    await callback.message.edit_text(f"Вы выбрали пользователя с ID: {target_id}\n\nВведите сумму перевода (числом):")
    await callback.answer()

@router.message(PayStates.waiting_for_amount)
async def process_pay_amount(message: Message, db: Database, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return
        
    data = await state.get_data()
    target_id = data.get("pay_target_id")
    
    sender = await db.get_user(message.from_user.id)
    if sender.coins < amount:
        await message.answer(f"Недостаточно средств! У вас {sender.coins} 🪙.")
        await state.clear()
        return
        
    target = await db.get_user(target_id)
    sender.coins -= amount
    target.coins += amount
    await db.update_user(sender)
    await db.update_user(target)
    await db.add_transaction(sender.id, target.id, amount, "user_transfer")
    
    await message.answer(f"Успешно переведено {amount} 🪙 пользователю {target_id}!")
    try:
        await bot.send_message(target_id, f"💸 Вам пришел перевод: {amount} 🪙 от пользователя {message.from_user.id}!")
    except:
        pass
        
    await state.clear()

@router.callback_query(F.data == "back_to_economy")
async def cb_back_to_economy(callback: CallbackQuery):
    await callback.message.edit_text("Добро пожаловать в раздел Игр и Экономики! Выберите действие:", reply_markup=get_economy_menu())
    await callback.answer()

# --- Бизнесы ---
@router.callback_query(F.data == "eco_businesses")
async def cb_eco_businesses(callback: CallbackQuery, db: Database):
    businesses = await db.get_user_businesses(callback.from_user.id)
    text = "💼 **Ваши Бизнесы**\n\n"
    if not businesses:
        text += "У вас пока нет бизнесов. Купите один, чтобы получать пассивный доход!"
    else:
        for b in businesses:
            name = "Магазин Манги" if b[2] == 'manga' else "Аркадный автомат"
            text += f"🏢 {name} (Сейф заполняется 12 часов)\n"
            
    await callback.message.edit_text(text, reply_markup=get_businesses_kb(businesses))

@router.callback_query(F.data.startswith("buy_biz_"))
async def cb_buy_biz(callback: CallbackQuery, db: Database):
    biz_type = callback.data.split("_")[2]
    user = await db.get_user(callback.from_user.id)
    cost = 500 if biz_type == 'manga' else 2000
    
    if user.coins < cost:
        await callback.answer(f"Недостаточно средств. Нужно {cost} 🪙.", show_alert=True)
        return
        
    user.coins -= cost
    await db.update_user(user)
    await db.add_business(user.id, biz_type)
    await db.add_transaction(user.id, 0, cost, f"buy_biz_{biz_type}")
    
    await callback.answer("Бизнес успешно куплен!", show_alert=True)
    await cb_eco_businesses(callback, db) # Refresh

@router.callback_query(F.data == "collect_biz")
async def cb_collect_biz(callback: CallbackQuery, db: Database):
    businesses = await db.get_user_businesses(callback.from_user.id)
    if not businesses: return
    
    now = time.time()
    total_profit = 0
    for b in businesses:
        biz_id = b[0]
        biz_type = b[2]
        last_collect = b[3]
        
        hours_passed = (now - last_collect) / 3600
        if hours_passed > 12: hours_passed = 12 # Max 12 hours
        
        hourly_rate = 10 if biz_type == 'manga' else 50
        profit = int(hours_passed * hourly_rate)
        
        if profit > 0:
            total_profit += profit
            await db.update_business_collect_time(biz_id, now)
            
    if total_profit > 0:
        user = await db.get_user(callback.from_user.id)
        user.coins += total_profit
        await db.update_user(user)
        await db.add_transaction(0, user.id, total_profit, "biz_collect")
        await callback.answer(f"Собрана прибыль: {total_profit} 🪙!", show_alert=True)
    else:
        await callback.answer("Прибыль еще не накопилась.", show_alert=True)

# --- Магазин ---
@router.callback_query(F.data == "eco_shop")
async def cb_eco_shop(callback: CallbackQuery):
    text = "🏪 **Магазин Баффов и Титулов**\n\nЗдесь можно купить полезные предметы за коины."
    await callback.message.edit_text(text, reply_markup=get_shop_kb())

@router.callback_query(F.data.startswith("shop_buy_"))
async def cb_shop_buy(callback: CallbackQuery, db: Database):
    item = callback.data.replace("shop_buy_", "")
    user = await db.get_user(callback.from_user.id)
    
    if item == "energy": cost = 150
    elif item == "ramen": cost = 300
    elif item == "title_sempai": cost = 1000
    else: cost = 0
    
    if user.coins < cost:
        await callback.answer(f"Недостаточно коинов. Нужно {cost} 🪙", show_alert=True)
        return
        
    user.coins -= cost
    if item == "ramen":
        user.trust += 10
        await callback.answer("Вы съели рамен! Доверие Махиро выросло на +10%", show_alert=True)
    elif item == "energy":
        user.xp += 200 # For now, just give flat XP instead of complex 24h buff
        await callback.answer("Вы выпили энергетик! +200 XP", show_alert=True)
    elif item == "title_sempai":
        await db.add_inventory_item(user.id, "title", "Семпай")
        await callback.answer("Вы купили титул 'Семпай'!", show_alert=True)
        
    await db.update_user(user)
    await db.add_transaction(user.id, 0, cost, f"shop_{item}")

# --- Банк ---
@router.callback_query(F.data == "eco_bank")
async def cb_eco_bank(callback: CallbackQuery, db: Database):
    records = await db.get_user_bank_records(callback.from_user.id)
    deposits = sum(r[3] for r in records if r[2] == 'deposit')
    loans = sum(r[3] for r in records if r[2] == 'loan')
    
    text = f"🏦 **Банк Махиро**\n\nВаши вклады: {deposits} 🪙\nВаши долги: {loans} 🪙\n\nПроцент по вкладу: 2% в день.\nКредит нужно вернуть за 7 дней."
    await callback.message.edit_text(text, reply_markup=get_bank_kb())

@router.callback_query(F.data == "bank_deposit")
async def cb_bank_deposit(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    if user.coins < 1000:
        await callback.answer("Для вклада нужно минимум 1000 🪙", show_alert=True)
        return
    user.coins -= 1000
    await db.update_user(user)
    await db.add_bank_record(user.id, "deposit", 1000)
    await db.add_transaction(user.id, 0, 1000, "bank_deposit")
    await callback.answer("Вклад на 1000 🪙 успешно открыт!", show_alert=True)
    await cb_eco_bank(callback, db)
    
@router.callback_query(F.data == "bank_withdraw")
async def cb_bank_withdraw(callback: CallbackQuery, db: Database):
    records = await db.get_user_bank_records(callback.from_user.id)
    deposit_records = [r for r in records if r[2] == 'deposit']
    if not deposit_records:
        await callback.answer("У вас нет вкладов.", show_alert=True)
        return
        
    # Simplify: withdraw all deposits
    now = time.time()
    total_amount = 0
    for r in deposit_records:
        days = (now - r[4]) / 86400
        amount = r[3]
        profit = amount * 0.02 * days
        total_amount += int(amount + profit)
        # Delete record
        await db._conn.execute('DELETE FROM bank_records WHERE id = ?', (r[0],))
        
    user = await db.get_user(callback.from_user.id)
    user.coins += total_amount
    await db.update_user(user)
    await db._conn.commit()
    await db.add_transaction(0, user.id, total_amount, "bank_withdraw")
    
    await callback.answer(f"Вклады закрыты. Получено: {total_amount} 🪙", show_alert=True)
    await cb_eco_bank(callback, db)

# --- Контракты (Placeholder) ---
@router.callback_query(F.data == "eco_contracts")
async def cb_eco_contracts(callback: CallbackQuery):
    await callback.answer("Контракты в разработке! Ожидайте в следующем патче.", show_alert=True)

# --- Казино PvP (Coinflip) ---
@router.callback_query(F.data == "eco_casino")
async def cb_eco_casino(callback: CallbackQuery, db: Database, state: FSMContext):
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    if not users:
        await callback.answer("Нет соперников для игры.", show_alert=True)
        return
    await state.set_state(CasinoStates.waiting_for_opponent)
    await callback.message.edit_text("🎲 **Coinflip (Орел и Решка)**\n\nВыберите соперника, которому хотите бросить вызов:", reply_markup=get_pay_users_kb(users, 0))

@router.callback_query(CasinoStates.waiting_for_opponent, F.data.startswith("pay_page_"))
async def casino_paginate(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    await callback.message.edit_reply_markup(reply_markup=get_pay_users_kb(users, page))
    await callback.answer()

@router.callback_query(CasinoStates.waiting_for_opponent, F.data.startswith("pay_select_"))
async def casino_select_opponent(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    await state.update_data(casino_target_id=target_id)
    await state.set_state(CasinoStates.waiting_for_bet)
    await callback.message.edit_text(f"Вы выбрали соперника с ID: {target_id}\n\nВведите ставку коинов (числом):")
    await callback.answer()

@router.callback_query(CasinoStates.waiting_for_opponent, F.data == "pay_cancel")
async def casino_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добро пожаловать в раздел Игр и Экономики! Выберите действие:", reply_markup=get_economy_menu())
    await callback.answer()

@router.message(CasinoStates.waiting_for_bet)
async def process_casino_bet(message: Message, db: Database, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return
        
    data = await state.get_data()
    target_id = data.get("casino_target_id")
    
    sender = await db.get_user(message.from_user.id)
    if sender.coins < amount:
        await message.answer(f"Недостаточно средств! У вас {sender.coins} 🪙.")
        await state.clear()
        return
        
    target = await db.get_user(target_id)
    if target.coins < amount:
        await message.answer(f"У соперника недостаточно средств для ставки {amount} 🪙.")
        await state.clear()
        return
        
    # Play
    sender.coins -= amount
    target.coins -= amount
    
    roll = random.choice([True, False]) # True = Sender wins
    win_amount = amount * 2
    
    if roll:
        sender.coins += win_amount
        winner_id, loser_id = sender.id, target.id
        result_text = f"🎉 Поздравляем! Вы выиграли Coinflip против {target_id} и забрали {win_amount} 🪙!"
        target_text = f"💔 Вы проиграли {amount} 🪙 в Coinflip против {sender.id}."
    else:
        target.coins += win_amount
        winner_id, loser_id = target.id, sender.id
        result_text = f"💔 Вы проиграли {amount} 🪙 в Coinflip против {target_id}."
        target_text = f"🎉 Поздравляем! Пользователь {sender.id} бросил вам вызов в Coinflip и проиграл. Вы забрали {win_amount} 🪙!"
        
    await db.update_user(sender)
    await db.update_user(target)
    await db.add_transaction(loser_id, winner_id, amount, "casino_coinflip")
    
    await message.answer(result_text)
    try:
        await bot.send_message(target_id, target_text)
    except: pass
    
    await state.clear()

# --- Брак (Placeholder) ---
@router.callback_query(F.data == "eco_marry")
async def cb_eco_marry(callback: CallbackQuery):
    await callback.answer("Система брака в разработке!", show_alert=True)

# --- Репутация (Placeholder) ---
@router.callback_query(F.data == "eco_rep")
async def cb_eco_rep(callback: CallbackQuery):
    await callback.answer("Система репутации в разработке!", show_alert=True)

# --- Quiz (Placeholder for now, redirect) ---
@router.callback_query(F.data == "eco_quiz")
async def cb_eco_quiz(callback: CallbackQuery):
    await callback.message.answer("Чтобы играть в квиз, напишите /quiz (интеграция в кнопки в процессе)")
    await callback.answer()
