from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
from bot.fsm.states import ShopStates

router = Router()

def get_market_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"market_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"market_page_{page+1}"))
        
    kb = []
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton(text="➕ Продать предмет", callback_data="market_sell")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_economy")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_market")
async def cb_market(callback: CallbackQuery, db: Database):
    await show_market(callback, db, 0)
    
@router.callback_query(F.data.startswith("market_page_"))
async def cb_market_page(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[-1])
    await show_market(callback, db, page)

async def show_market(callback: CallbackQuery, db: Database, page: int):
    async with db._conn.execute('SELECT m.id, m.seller_id, m.item_type, m.item_id, m.price, u.username FROM market_lots m JOIN users u ON m.seller_id = u.id ORDER BY m.id DESC') as cursor:
        lots = await cursor.fetchall()
        
    if not lots:
        await callback.message.edit_text("🛒 **Глобальный Рынок**\n\nЗдесь пока пусто. Вы можете выставить свои вещи на продажу первыми!", reply_markup=get_market_kb(0, 1))
        return
        
    items_per_page = 5
    total_pages = (len(lots) - 1) // items_per_page + 1
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * items_per_page
    page_lots = lots[start_idx:start_idx+items_per_page]
    
    text = f"🛒 **Глобальный Рынок** (Стр. {page+1}/{total_pages})\nПокупайте вещи у других игроков!\n\n"
    
    kb = []
    for lot in page_lots:
        l_id, s_id, i_type, i_id, price, s_name = lot
        seller_name = s_name if s_name else f"ID:{s_id}"
        
        item_name = f"Неизвестно ({i_type})"
        if i_type == "card":
            async with db._conn.execute('SELECT name FROM cards WHERE id = ?', (i_id,)) as c:
                row = await c.fetchone()
                if row: item_name = f"Карточка: {row[0]}"
                
        text += f"📦 **{item_name}**\nПродавец: {seller_name} | Цена: {price} 🪙\n\n"
        kb.append([InlineKeyboardButton(text=f"Купить {item_name} за {price} 🪙", callback_data=f"market_buy_{l_id}")])
        
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"market_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"market_page_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="➕ Выставить предмет", callback_data="market_sell")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_economy")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("market_buy_"))
async def cb_market_buy(callback: CallbackQuery, db: Database):
    lot_id = int(callback.data.split("_")[-1])
    
    async with db._conn.execute('SELECT id, seller_id, item_type, item_id, price FROM market_lots WHERE id = ?', (lot_id,)) as cursor:
        lot = await cursor.fetchone()
        
    if not lot:
        await callback.answer("Этот лот уже был куплен или удален!", show_alert=True)
        return
        
    _, s_id, i_type, i_id, price = lot
    
    if s_id == callback.from_user.id:
        await callback.answer("Вы не можете купить свой же лот!", show_alert=True)
        return
        
    buyer = await db.get_user(callback.from_user.id)
    if buyer.coins < price:
        await callback.answer("Недостаточно средств для покупки!", show_alert=True)
        return
        
    # Process transaction
    buyer.coins -= price
    await db.update_user(buyer)
    
    seller = await db.get_user(s_id)
    seller.coins += price
    await db.update_user(seller)
    
    # Give item
    if i_type == "card":
        await db.add_user_card(buyer.id, i_id)
        
    # Delete lot
    await db._conn.execute('DELETE FROM market_lots WHERE id = ?', (lot_id,))
    await db._conn.commit()
    
    await callback.answer("Покупка успешно завершена!", show_alert=True)
    await cb_market(callback, db) # refresh UI

@router.callback_query(F.data == "market_sell")
async def cb_market_sell(callback: CallbackQuery):
    text = ("Чтобы продать предмет на глобальном рынке, используйте команду:\n\n"
            "`/sell card [Ваша_Карточка_ID] [Цена]`\n\n"
            "Вы можете посмотреть ID ваших карточек в меню Гачи (Скоро добавим туда отображение ID).")
    await callback.answer(text, show_alert=True)

@router.message(F.text.startswith("/sell "))
async def cmd_sell(message: Message, db: Database):
    args = message.text.split()
    if len(args) != 4 or args[1] != "card":
        await message.answer("Использование: /sell card [ID] [Цена]")
        return
        
    try:
        c_id = int(args[2])
        price = int(args[3])
    except ValueError:
        await message.answer("ID и Цена должны быть числами!")
        return
        
    if price < 1:
        await message.answer("Цена должна быть больше 0.")
        return
        
    # Check if user has this card
    user_cards = await db.get_user_cards(message.from_user.id)
    has_card = False
    for uc in user_cards:
        # uc: uc.id, uc.card_id, uc.level, c.name, c.rarity, c.stats, c.image_path
        if uc[1] == c_id:
            has_card = True
            break
            
    if not has_card:
        await message.answer("У вас нет такой карточки!")
        return
        
    # Ideally we'd remove the card or decrease its level, but for now we just list it and remove it.
    await db._conn.execute('UPDATE user_cards SET level = level - 1 WHERE user_id = ? AND card_id = ?', (message.from_user.id, c_id))
    await db._conn.execute('DELETE FROM user_cards WHERE level <= 0')
    
    await db._conn.execute('INSERT INTO market_lots (seller_id, item_type, item_id, price) VALUES (?, ?, ?, ?)', (message.from_user.id, "card", c_id, price))
    await db._conn.commit()
    
    await message.answer(f"✅ Карточка выставлена на глобальный рынок за {price} 🪙!")
