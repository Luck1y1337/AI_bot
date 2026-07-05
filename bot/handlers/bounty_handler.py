from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class BountyStates(StatesGroup):
    waiting_for_bounty_amount = State()

def get_bounty_kb(bounties: list) -> InlineKeyboardMarkup:
    kb = []
    for target_id, amount in bounties:
        kb.append([InlineKeyboardButton(text=f"🎯 Игрок {target_id} | 🪙 {amount}", callback_data=f"bounty_info_{target_id}")])
        
    kb.append([InlineKeyboardButton(text="➕ Назначить Награду", callback_data="bounty_add")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cat_social")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_bounties")
async def cb_bounties_menu(callback: CallbackQuery, db: Database):
    bounties = await db.get_all_bounties()
    
    text = "🎯 <b>Доска Наград (Bounty Board)</b>\n\nСамые разыскиваемые игроки сервера!\nПобедите их в Казино Коинфлип, чтобы забрать награду."
    
    if not bounties:
        text += "\n\nПока никто не находится в розыске."
        
    await callback.message.edit_text(text, reply_markup=get_bounty_kb(bounties))
    await callback.answer()

@router.callback_query(F.data == "bounty_add")
async def cb_bounty_add(callback: CallbackQuery, db: Database, state: FSMContext):
    from bot.keyboards.main_kb import get_social_users_kb
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    
    if not users:
        return await callback.answer("На сервере больше нет игроков.", show_alert=True)
        
    # We reuse the pay_select callback for simplicity, but we need to know we're in bounty mode
    await state.set_state(BountyStates.waiting_for_bounty_amount)
    await callback.message.edit_text("🎯 <b>Назначить Награду</b>\n\nВыберите игрока, за чью голову вы хотите назначить награду:", reply_markup=get_social_users_kb(users, 0))

@router.callback_query(BountyStates.waiting_for_bounty_amount, F.data.startswith("pay_select_"))
async def cb_bounty_select_target(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    await state.update_data(bounty_target=target_id)
    await callback.message.edit_text(f"Вы выбрали игрока {target_id}. Введите сумму награды 🪙 (будет списана с вашего баланса):")
    
@router.message(BountyStates.waiting_for_bounty_amount)
async def process_bounty_amount(message: Message, state: FSMContext, db: Database, bot: Bot):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except Exception:
        return await message.answer("Пожалуйста, введите корректное положительное число.")
        
    data = await state.get_data()
    target_id = data.get("bounty_target")
    
    if not target_id:
        return await state.clear()
        
    if not await db.deduct_coins(message.from_user.id, amount):
        await message.answer("Недостаточно коинов на балансе!")
        await state.clear()
        return
        
    await db.add_bounty(target_id, message.from_user.id, amount)
    await message.answer(f"✅ Вы успешно назначили награду в {amount} 🪙 за голову игрока {target_id}!")
    
    try:
        await bot.send_message(target_id, f"🚨 ВНИМАНИЕ! Игрок {message.from_user.id} назначил за вашу голову награду в {amount} 🪙!\nБудьте осторожны в Казино.")
    except Exception: pass
    
    await state.clear()
