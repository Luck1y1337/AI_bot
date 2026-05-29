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
        
    text = (f"🐾 **Ваш Питомец** {emoji}\n\n"
            f"Имя: {p_name}\n"
            f"Сытость: {hunger}/100 🍖\n"
            f"Счастье: {happiness}/100 🎾\n\n"
            f"Статус: {status_text}\n"
            f"*(Питомцы дают пассивные баффы в RPG рейдах)*")
            
    if message.from_user.id == message.bot.id:
        await message.edit_text(text, reply_markup=get_pet_kb())
    else:
        await message.answer(text, reply_markup=get_pet_kb())

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
    
    if time.time() - last_interact < 60:
        await callback.answer("Питомец пока не хочет этого! Подождите минуту.", show_alert=True)
        return
        
    if callback.data == "pet_feed":
        hunger = min(100, hunger + 20)
        msg = f"Вы покормили {p_name}! Сытость +20"
    else:
        happiness = min(100, happiness + 20)
        msg = f"Вы поиграли с {p_name}! Счастье +20"
        
    await db.update_user_pet(p_id, hunger, happiness, time.time())
    await callback.answer(msg, show_alert=True)
    await cb_menu_pet(callback, db)
