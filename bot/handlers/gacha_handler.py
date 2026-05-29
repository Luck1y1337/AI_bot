from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
import random
import time

router = Router()

def get_gacha_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎰 Крутить Гачу (500 🪙)", callback_data="gacha_roll")],
        [InlineKeyboardButton(text="🎴 Моя Коллекция", callback_data="gacha_collection_0")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_collection_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"gacha_collection_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"gacha_collection_{page+1}"))
        
    kb = []
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton(text="🔙 В меню гачи", callback_data="gacha_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "gacha_menu")
async def cb_gacha_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎰 **Гача-Автомат**\n\nЗдесь можно выбить уникальные карточки персонажей! Они дают бонусы к RPG статам.", reply_markup=get_gacha_kb())

@router.callback_query(F.data == "gacha_roll")
async def cb_gacha_roll(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    cost = 500
    
    if user.coins < cost:
        await callback.answer(f"Недостаточно коинов. Нужно {cost} 🪙", show_alert=True)
        return
        
    cards = await db.get_all_cards()
    if not cards:
        await callback.answer("В автомате пока нет карточек! Админы еще не завезли.", show_alert=True)
        return
        
    user.coins -= cost
    await db.update_user(user)
    
    # Rarity weights: Common 70%, Rare 20%, Epic 9%, Legendary 1%
    rarities = {"Common": 0, "Rare": 0, "Epic": 0, "Legendary": 0}
    weights = []
    for c in cards:
        r = c[2]
        if r == "Legendary": weights.append(1)
        elif r == "Epic": weights.append(9)
        elif r == "Rare": weights.append(20)
        else: weights.append(70)
        
    pulled = random.choices(cards, weights=weights, k=1)[0]
    await db.add_user_card(user.id, pulled[0])
    
    rarity_emojis = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡"}
    r_emoji = rarity_emojis.get(pulled[2], "⚪")
    
    text = f"🎉 **ВЫПАЛА КАРТОЧКА!** 🎉\n\n{r_emoji} **{pulled[1]}**\nРядкость: {pulled[2]}\nБонус к статам: +{pulled[3]}"
    await callback.message.edit_text(text, reply_markup=get_gacha_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("gacha_collection_"))
async def cb_gacha_collection(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[-1])
    cards = await db.get_user_cards(callback.from_user.id)
    
    if not cards:
        await callback.answer("У вас пока нет ни одной карточки.", show_alert=True)
        return
        
    items_per_page = 5
    total_pages = (len(cards) - 1) // items_per_page + 1
    
    if page >= total_pages:
        page = total_pages - 1
        
    start_idx = page * items_per_page
    page_cards = cards[start_idx:start_idx+items_per_page]
    
    text = f"🎴 **Ваша коллекция** (Стр. {page+1}/{total_pages})\n\n"
    rarity_emojis = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡"}
    
    for c in page_cards:
        # id, card_id, level, name, rarity, stats, image_path
        c_lvl = c[2]
        c_name = c[3]
        c_rarity = c[4]
        c_stats = c[5] * c_lvl
        emoji = rarity_emojis.get(c_rarity, "⚪")
        
        text += f"{emoji} **{c_name}** (Ур. {c_lvl})\n└ Мощь: {c_stats}\n\n"
        
    await callback.message.edit_text(text, reply_markup=get_collection_kb(page, total_pages))
