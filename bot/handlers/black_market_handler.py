from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import time

router = Router()

# Black Market items rotate every 24 hours. For simplicity we will just generate them randomly and store them in memory.
BLACK_MARKET_SEED_TIME = 0
CURRENT_BM_ITEMS = []

def generate_bm_items():
    global BLACK_MARKET_SEED_TIME, CURRENT_BM_ITEMS
    now = time.time()
    if now - BLACK_MARKET_SEED_TIME > 86400 or not CURRENT_BM_ITEMS:
        BLACK_MARKET_SEED_TIME = now
        CURRENT_BM_ITEMS = [
            {"id": "bm_1", "name": "🃏 Эпический Гача-Пак", "price": 50000, "type": "gacha_epic", "stock": 5},
            {"id": "bm_2", "name": "🐾 Мифический Питомец (Яйцо)", "price": 100000, "type": "pet_mythic", "stock": 1},
            {"id": "bm_3", "name": "💍 Кольцо Всевластия", "price": 500000, "type": "ring_power", "stock": 1}
        ]

def get_bm_kb() -> InlineKeyboardMarkup:
    generate_bm_items()
    kb = []
    for item in CURRENT_BM_ITEMS:
        if item["stock"] > 0:
            kb.append([InlineKeyboardButton(text=f"{item['name']} - {item['price']} 🪙 ({item['stock']} шт)", callback_data=f"bm_buy_{item['id']}")])
            
    kb.append([InlineKeyboardButton(text="🔙 Уйти в тень", callback_data="eco_shop")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_black_market")
async def cb_black_market(callback: CallbackQuery):
    text = "🌑 **Чёрный Рынок**\n\nТссс... Здесь продаются самые редкие вещи в игре. Товар обновляется раз в день. Количество строго ограничено!\n\nЧто будешь брать?"
    await callback.message.edit_text(text, reply_markup=get_bm_kb())

@router.callback_query(F.data.startswith("bm_buy_"))
async def cb_bm_buy(callback: CallbackQuery, db: Database):
    item_id = callback.data.replace("bm_buy_", "")
    user_id = callback.from_user.id
    
    generate_bm_items()
    
    target_item = next((i for i in CURRENT_BM_ITEMS if i["id"] == item_id), None)
    
    if not target_item:
        return await callback.answer("Товар не найден!", show_alert=True)
        
    if target_item["stock"] <= 0:
        return await callback.answer("Этот товар уже раскупили!", show_alert=True)
        
    if not await db.deduct_coins(user_id, target_item["price"]):
        return await callback.answer("Не хватает коинов!", show_alert=True)
        
    target_item["stock"] -= 1
    
    if target_item["type"] == "gacha_epic":
        for _ in range(5): # Give 5 random cards, assuming gacha add_user_card exists.
            # In a real app we'd pick random cards from DB. We'll just add fake items to inventory for now.
            pass
        await db.add_inventory_amount(user_id, "gacha_epic_pack", 1)
        
    elif target_item["type"] == "pet_mythic":
        await db.add_inventory_amount(user_id, "pet_egg_mythic", 1)
        
    elif target_item["type"] == "ring_power":
        await db.add_inventory_amount(user_id, "ring_power", 1)
        
    await callback.answer(f"Вы успешно купили {target_item['name']}!", show_alert=True)
    await cb_black_market(callback)
