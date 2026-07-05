from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import time

router = Router()

BM_CATALOG = [
    {"id": "bm_1", "name": "🃏 Эпический Гача-Пак", "price": 50000, "type": "gacha_epic", "stock": 5},
    {"id": "bm_2", "name": "🐾 Мифический Питомец (Яйцо)", "price": 100000, "type": "pet_mythic", "stock": 1},
    {"id": "bm_3", "name": "💍 Кольцо Всевластия", "price": 500000, "type": "ring_power", "stock": 1},
]


async def ensure_bm_seeded(db: Database):
    items = await db.get_black_market_items()
    if not items or (time.time() - items[0][5] > 86400):
        await db.seed_black_market(BM_CATALOG, time.time())


async def get_bm_kb(db: Database) -> InlineKeyboardMarkup:
    await ensure_bm_seeded(db)
    items = await db.get_black_market_items()
    kb = []
    for item_id, name, price, item_type, stock, seed_time in items:
        if stock > 0:
            kb.append([InlineKeyboardButton(
                text=f"{name} - {price} 🪙 ({stock} шт)",
                callback_data=f"bm_buy_{item_id}"
            )])
    kb.append([InlineKeyboardButton(text="🔙 Уйти в тень", callback_data="eco_shop")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.callback_query(F.data == "eco_black_market")
async def cb_black_market(callback: CallbackQuery, db: Database):
    text = "🌑 <b>Чёрный Рынок</b>\n\nТссс... Здесь продаются самые редкие вещи в игре. Товар обновляется раз в день. Количество строго ограничено!\n\nЧто будешь брать?"
    await callback.message.edit_text(text, reply_markup=await get_bm_kb(db))


@router.callback_query(F.data.startswith("bm_buy_"))
async def cb_bm_buy(callback: CallbackQuery, db: Database):
    item_id = callback.data.replace("bm_buy_", "")
    user_id = callback.from_user.id

    item = await db.get_bm_item(item_id)
    if not item:
        return await callback.answer("Товар не найден!", show_alert=True)

    bm_id, name, price, item_type, stock = item

    if stock <= 0:
        return await callback.answer("Этот товар уже раскупили!", show_alert=True)

    if not await db.deduct_coins(user_id, price):
        return await callback.answer("Не хватает коинов!", show_alert=True)

    if not await db.decrement_bm_stock(item_id):
        await db.add_coins(user_id, price)
        return await callback.answer("Этот товар уже раскупили!", show_alert=True)

    if item_type == "gacha_epic":
        cards = await db.get_all_cards()
        if cards:
            epic_and_above = [c for c in cards if c[2] in ("Epic", "Legendary")]
            pool = epic_and_above if epic_and_above else cards
            for _ in range(5):
                card = random.choice(pool)
                await db.add_user_card(user_id, card[0])
    elif item_type == "pet_mythic":
        await db.add_inventory_amount(user_id, "pet_egg_mythic", 1)
    elif item_type == "ring_power":
        await db.add_inventory_amount(user_id, "ring_power", 1)

    await callback.answer(f"Вы успешно купили {name}!", show_alert=True)
    await cb_black_market(callback, db)
