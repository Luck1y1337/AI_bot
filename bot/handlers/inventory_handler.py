from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.repository import Database
import time

router = Router()

def get_inventory_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="⛏️ Добывать Ресурсы", callback_data="inv_mine")],
        [InlineKeyboardButton(text="⚒️ Крафт", callback_data="inv_craft_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cat_income")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_craft_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🗡️ Меч (10 🪵, 5 🪨)", callback_data="craft_sword")],
        [InlineKeyboardButton(text="🛡️ Броня (20 🪵, 10 🪨)", callback_data="craft_armor")],
        [InlineKeyboardButton(text="💍 Обручальное Кольцо (50 🪨, 1000 🪙)", callback_data="craft_ring")],
        [InlineKeyboardButton(text="🔙 В инвентарь", callback_data="eco_inventory")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_inventory")
async def cb_inventory(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    
    # Let's get inventory with amounts
    # inventory: id, user_id, item_type, amount
    items = []
    async with db._conn.execute('SELECT item_type, amount FROM inventory WHERE user_id = ?', (user_id,)) as cursor:
        items = await cursor.fetchall()
        
    text = "🎒 <b>Ваш Инвентарь</b>\n\n"
    if not items:
        text += "Пусто. Отправляйтесь добывать ресурсы!"
    else:
        emojis = {
            "wood": "🪵 Дерево",
            "stone": "🪨 Камень",
            "sword": "🗡️ Меч",
            "armor": "🛡️ Броня",
            "ring": "💍 Обручальное Кольцо"
        }
        
        # Pagination
        items_per_page = 10
        total_pages = (len(items) - 1) // items_per_page + 1
        page = 0
        start_idx = page * items_per_page
        page_items = items[start_idx:start_idx+items_per_page]
        
        for item_type, amount in page_items:
            name = emojis.get(item_type, item_type)
            text += f"• {name}: {amount} шт.\n"
            
    await callback.message.edit_text(text, reply_markup=get_inventory_kb())
    await callback.answer()

@router.callback_query(F.data == "inv_mine")
async def cb_inv_mine(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    
    # Cooldown 15 minutes
    async with db._conn.execute('SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = "mine" ORDER BY timestamp DESC LIMIT 1', (user_id,)) as cursor:
        last_mine = await cursor.fetchone()
        
    if last_mine and time.time() - last_mine[0] < 900:
        mins = int(15 - (time.time() - last_mine[0]) / 60)
        return await callback.answer(f"Вы устали! Отдохните еще {mins} мин.", show_alert=True)
        
    import random
    wood = random.randint(1, 5)
    stone = random.randint(0, 3)
    
    await db.add_inventory_amount(user_id, "wood", wood)
    if stone > 0:
        await db.add_inventory_amount(user_id, "stone", stone)
        
    await db.add_transaction(user_id, 0, 0, "mine")
    
    msg = f"Вы поработали в шахте и лесу!\nПолучено: 🪵 {wood} Дерева"
    if stone > 0: msg += f", 🪨 {stone} Камня"
    
    await callback.answer(msg, show_alert=True)
    await cb_inventory(callback, db)

@router.callback_query(F.data == "inv_craft_menu")
async def cb_craft_menu(callback: CallbackQuery):
    text = "⚒️ <b>Верстак</b>\n\nВыберите, что хотите скрафтить:"
    await callback.message.edit_text(text, reply_markup=get_craft_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("craft_"))
async def cb_craft_item(callback: CallbackQuery, db: Database):
    item = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    async def get_amount(item_type):
        inv = await db.get_inventory_item(user_id, item_type)
        return inv[2] if inv else 0
        
    wood = await get_amount("wood")
    stone = await get_amount("stone")
    
    if item == "sword":
        if wood < 10 or stone < 5:
            return await callback.answer("Не хватает ресурсов! Нужно 10 🪵 и 5 🪨", show_alert=True)
        await db.remove_inventory_amount(user_id, "wood", 10)
        await db.remove_inventory_amount(user_id, "stone", 5)
        await db.add_inventory_amount(user_id, "sword", 1)
        name = "🗡️ Меч"
    elif item == "armor":
        if wood < 20 or stone < 10:
            return await callback.answer("Не хватает ресурсов! Нужно 20 🪵 и 10 🪨", show_alert=True)
        await db.remove_inventory_amount(user_id, "wood", 20)
        await db.remove_inventory_amount(user_id, "stone", 10)
        await db.add_inventory_amount(user_id, "armor", 1)
        name = "🛡️ Броня"
    elif item == "ring":
        if stone < 50:
            return await callback.answer("Не хватает ресурсов! Нужно 50 🪨", show_alert=True)
        if not await db.deduct_coins(user_id, 1000):
            return await callback.answer("Не хватает 1000 🪙", show_alert=True)
        await db.remove_inventory_amount(user_id, "stone", 50)
        await db.add_inventory_amount(user_id, "ring", 1)
        name = "💍 Обручальное Кольцо"
    else:
        return
        
    await callback.answer(f"Вы успешно создали {name}!", show_alert=True)
    await cb_inventory(callback, db)
