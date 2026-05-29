from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database

router = Router()

@router.message(F.text.in_(["/inventory", "🎒 Инвентарь"]))
async def cmd_inventory(message: Message, db: Database):
    inventory = await db.get_user_inventory(message.from_user.id)
    
    if not inventory:
        await message.answer("Ваш инвентарь пуст.")
        return
        
    items = {}
    for item in inventory:
        item_type = item[2]
        item_val = item[3]
        key = f"{item_type}:{item_val}"
        items[key] = items.get(key, 0) + 1
        
    text = "🎒 **Ваш Инвентарь:**\n\n"
    for key, count in items.items():
        t, v = key.split(":")
        emoji = "📦"
        if t == "material": emoji = "⛏️"
        elif t == "title": emoji = "🎖️"
        elif t == "pet": emoji = "🐾"
        
        text += f"{emoji} {v} (x{count})\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔨 Крафт Питомца", callback_data="craft_pet")]
    ])
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "craft_pet")
async def cb_craft_pet(callback: CallbackQuery, db: Database):
    inventory = await db.get_user_inventory(callback.from_user.id)
    materials = [item for item in inventory if item[2] == "material"]
    
    wood = sum(1 for m in materials if m[3] == "Дерево")
    metal = sum(1 for m in materials if m[3] == "Металл")
    crystal = sum(1 for m in materials if m[3] == "Кристалл")
    
    text = "🔨 **Крафт Питомца**\n\nДля создания Питомца-Помощника (+20% XP) нужно:\n"
    text += f"- Дерево: {wood}/2\n"
    text += f"- Металл: {metal}/2\n"
    text += f"- Кристалл: {crystal}/1\n\n"
    
    if wood >= 2 and metal >= 2 and crystal >= 1:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Создать Питомца!", callback_data="do_craft_pet")]
        ])
    else:
        text += "❌ У вас недостаточно материалов. Выполняйте контракты (квесты) чтобы найти их."
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "do_craft_pet")
async def cb_do_craft_pet(callback: CallbackQuery, db: Database):
    # In a real app we'd delete the specific material rows. 
    # For now we'll just delete matching items by executing raw sql.
    for mat_name, count in [("Дерево", 2), ("Металл", 2), ("Кристалл", 1)]:
        await db._conn.execute('DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE user_id = ? AND item_type = "material" AND item_value = ? LIMIT ?)', (callback.from_user.id, mat_name, count))
    
    await db.add_inventory_item(callback.from_user.id, "pet", "Слайм-Помощник")
    await db._conn.commit()
    
    await callback.message.edit_text("🎉 **Успех!** Вы скрафтили **Слайма-Помощника**!\nТеперь вы получаете больше XP.")
