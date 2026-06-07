from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
import time
from utils.formatting import generate_progress_bar
import random

router = Router()

def get_pet_kb(pet_level: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🍖 Покормить (10 🪙)", callback_data="pet_feed"),
         InlineKeyboardButton(text="🎾 Поиграть", callback_data="pet_play")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_no_pet_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🐾 Приютить Слайма (Бесплатно)", callback_data="pet_adopt_slime")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_pet_evolution(pet_type: str, level: int) -> tuple[str, str]:
    if pet_type == "slime":
        if level < 10: return "Слайм", "💧"
        elif level < 20: return "Слайм-Рыцарь", "🗡️"
        else: return "Король Слаймов", "👑"
    return "Неизвестно", "❓"

@router.message(F.text == "🐾 Мой Питомец")
async def cmd_pet(message: Message, db: Database):
    await show_pet_ui(message, message.from_user.id, db)

@router.callback_query(F.data == "eco_pets")
async def cb_menu_pet(callback: CallbackQuery, db: Database):
    await show_pet_ui(callback.message, callback.from_user.id, db)
    await callback.answer()

async def show_pet_ui(message: Message, user_id: int, db: Database):
    pets = await db.get_user_pets(user_id)
    if not pets:
        text = "🐾 <b>Тамагочи</b>\n\nУ вас пока нет питомца! Возьмите себе слайма и заботьтесь о нем.\nСытый питомец приносит пассивный доход!"
        if isinstance(message, Message) and message.from_user.id != message.bot.id:
            await message.answer(text, reply_markup=get_no_pet_kb(), parse_mode="HTML")
        else:
            await message.edit_text(text, reply_markup=get_no_pet_kb(), parse_mode="HTML")
        return
        
    p_id, u_id, p_type, p_name, level, exp, hunger, last_fed = pets[0]
    
    hours_passed = (time.time() - last_fed) / 3600
    decay = int(hours_passed * 10) # -10 hunger per hour
    
    if decay > 0:
        hunger = max(0, hunger - decay)
        await db.update_pet(p_id, level, exp, hunger, time.time())
        
    form_name, emoji = get_pet_evolution(p_type, level)
    
    status_text = "Сыт и счастлив 😊 (+XP бафф активен)"
    if hunger < 50:
        status_text = "Голоден 😢 (Баффы отключены!)"
        
    hunger_bar = generate_progress_bar(hunger, 100, length=10)
    exp_bar = generate_progress_bar(exp, 100, length=10)
        
    text = f"🐾 <b>Ваш Питомец: {emoji} {form_name} {p_name}</b>\n\n"
    text += f"📊 <b>Уровень:</b> {level}\n"
    text += f"🌟 <b>Опыт:</b> {exp_bar} {exp}/100\n"
    text += f"🍖 <b>Сытость:</b> {hunger_bar} {hunger}/100\n"
    text += f"💭 <b>Статус:</b> {status_text}\n\n"
    text += "<i>Не забывайте навещать питомца!</i>"
    
    if isinstance(message, Message) and message.from_user.id != message.bot.id:
        await message.answer(text, reply_markup=get_pet_kb(level), parse_mode="HTML")
    else:
        await message.edit_text(text, reply_markup=get_pet_kb(level), parse_mode="HTML")

@router.callback_query(F.data.startswith("pet_adopt_"))
async def cb_pet_adopt(callback: CallbackQuery, db: Database):
    p_type = callback.data.split("_")[-1]
    name = "Римуру" if p_type == "slime" else "Неизвестный"
    
    pets = await db.get_user_pets(callback.from_user.id)
    if pets: return await callback.answer("У вас уже есть питомец!", show_alert=True)
    
    await db.create_pet(callback.from_user.id, p_type, name)
    await callback.answer("Вы успешно приютили слайма!", show_alert=True)
    await cb_menu_pet(callback, db)

@router.callback_query(F.data == "pet_feed")
async def cb_pet_feed(callback: CallbackQuery, db: Database):
    pets = await db.get_user_pets(callback.from_user.id)
    if not pets: return
        
    p_id, u_id, p_type, p_name, level, exp, hunger, last_fed = pets[0]
    
    if hunger >= 100:
        return await callback.answer("Питомец уже сыт!", show_alert=True)
        
    if not await db.deduct_coins(callback.from_user.id, 10):
        return await callback.answer("У вас нет 10 🪙 на еду!", show_alert=True)
        
    new_hunger = min(100, hunger + 30)
    await db.update_pet(p_id, level, exp, new_hunger, time.time())
    await db.add_transaction(callback.from_user.id, 0, 10, "pet_feed")
    
    await callback.answer(f"{p_name} вкусно покушал! Сытость +30", show_alert=True)
    await cb_menu_pet(callback, db)

@router.callback_query(F.data == "pet_play")
async def cb_pet_play(callback: CallbackQuery, db: Database):
    pets = await db.get_user_pets(callback.from_user.id)
    if not pets: return
        
    p_id, u_id, p_type, p_name, level, exp, hunger, last_fed = pets[0]
    
    if hunger < 20:
        return await callback.answer("Питомец слишком голоден для игр! Покормите его.", show_alert=True)
        
    async with db._conn.execute("SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = 'pet_play' ORDER BY timestamp DESC LIMIT 1", (callback.from_user.id,)) as cursor:
        last_action = await cursor.fetchone()
        
    if last_action and time.time() - last_action[0] < 3600:
        mins = int(60 - (time.time() - last_action[0]) / 60)
        return await callback.answer(f"Питомец устал! Поиграйте с ним через {mins} мин.", show_alert=True)
        
    new_exp = exp + 20
    new_hunger = max(0, hunger - 10)
    new_level = level
    
    if new_exp >= 100:
        new_level += 1
        new_exp = 0
        await callback.answer(f"🎉 Ваш питомец достиг {new_level} уровня!", show_alert=True)
    else:
        await callback.answer(f"Вы поиграли с {p_name}! +20 Опыта, -10 Сытость", show_alert=True)
        
    await db.update_pet(p_id, new_level, new_exp, new_hunger, time.time())
    await db.add_transaction(callback.from_user.id, 0, 0, "pet_play")
    await cb_menu_pet(callback, db)

