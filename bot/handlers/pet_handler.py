from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
import time

router = Router()

def get_pet_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🍖 Покормить", callback_data="pet_feed"),
         InlineKeyboardButton(text="🎾 Поиграть", callback_data="pet_play")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_no_pet_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🐱 Взять котенка (Бесплатно)", callback_data="pet_adopt_cat")],
        [InlineKeyboardButton(text="🐶 Взять щенка (Бесплатно)", callback_data="pet_adopt_dog")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(F.text == "🐾 Мой Питомец")
async def cmd_pet(message: Message, db: Database):
    await show_pet_ui(message, message.from_user.id, db)

@router.callback_query(F.data == "menu_pet")
async def cb_menu_pet(callback: CallbackQuery, db: Database):
    await show_pet_ui(callback.message, callback.from_user.id, db)
    await callback.answer()

async def show_pet_ui(message: Message, user_id: int, db: Database):
    pet = await db.get_user_pet(user_id)
    if not pet:
        if isinstance(message, Message) and message.from_user.id != message.bot.id:
            await message.answer("У вас пока нет питомца! Выберите кого хотите приютить:", reply_markup=get_no_pet_kb())
        else:
            await message.edit_text("У вас пока нет питомца! Выберите кого хотите приютить:", reply_markup=get_no_pet_kb())
        return
        
    # pet: id, user_id, pet_type, name, hunger, happiness, last_interact
    p_id, u_id, p_type, p_name, hunger, happiness, last_interact = pet
    
    # Calculate decay
    hours_passed = (time.time() - last_interact) / 3600
    decay = int(hours_passed * 5) # 5 points per hour
    
    if decay > 0:
        hunger = max(0, hunger - decay)
        happiness = max(0, happiness - decay)
        await db.update_user_pet(p_id, hunger, happiness, time.time())
        
    emoji = "🐱" if p_type == "cat" else "🐶"
    
    status_text = "Счастлив 😊"
    if hunger < 30 or happiness < 30:
        status_text = "Грустит 😢 (Нужен уход!)"
        
    from utils.formatting import generate_progress_bar
    hunger_bar = generate_progress_bar(hunger, 100, length=10)
    happiness_bar = generate_progress_bar(happiness, 100, length=10)
        
    text = f"🐾 <b>Ваш питомец {emoji} {p_name}</b>\n\n"
    text += f"🍗 <b>Сытость:</b> {hunger_bar} {hunger}/100\n"
    text += f"🎾 <b>Счастье:</b> {happiness_bar} {happiness}/100\n"
    text += f"💭 <b>Статус:</b> {status_text}\n\n"
    text += "<i>Не забывайте навещать питомца!</i>"
    
    if isinstance(message, Message) and message.from_user.id != message.bot.id:
        await message.answer(text, reply_markup=get_pet_kb(), parse_mode="HTML")
    else:
        await message.edit_text(text, reply_markup=get_pet_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("pet_adopt_"))
async def cb_pet_adopt(callback: CallbackQuery, db: Database):
    p_type = callback.data.split("_")[-1]
    name = "Барсик" if p_type == "cat" else "Бобик"
    
    await db.create_user_pet(callback.from_user.id, p_type, name)
    await callback.answer("Вы успешно приютили питомца!", show_alert=True)
    await cb_menu_pet(callback, db) # Refresh UI
    
@router.callback_query(F.data.in_(["pet_feed", "pet_play"]))
async def cb_pet_interact(callback: CallbackQuery, db: Database):
    pet = await db.get_user_pet(callback.from_user.id)
    if not pet:
        return
        
    p_id, u_id, p_type, p_name, hunger, happiness, last_interact = pet
    
    action_type = callback.data
    async with db._conn.execute('SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = ? ORDER BY timestamp DESC LIMIT 1', (callback.from_user.id, action_type)) as cursor:
        last_action = await cursor.fetchone()
        
    if last_action and time.time() - last_action[0] < 60:
        await callback.answer("Питомец пока не хочет этого! Подождите минуту.", show_alert=True)
        return
        
    if action_type == "pet_feed":
        hunger = min(100, hunger + 20)
        msg = f"Вы покормили {p_name}! Сытость +20"
    else:
        happiness = min(100, happiness + 20)
        msg = f"Вы поиграли с {p_name}! Счастье +20"
        
    await db.update_user_pet(p_id, hunger, happiness, time.time())
    await db.add_transaction(callback.from_user.id, 0, 0, action_type)
    await callback.answer(msg, show_alert=True)
    await cb_menu_pet(callback, db)
