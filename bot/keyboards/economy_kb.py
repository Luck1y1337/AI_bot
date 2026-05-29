from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_businesses_kb(businesses: list) -> InlineKeyboardMarkup:
    kb = []
    if not businesses:
        kb.append([InlineKeyboardButton(text="🏢 Купить Магазин Манги (500 🪙)", callback_data="buy_biz_manga")])
        kb.append([InlineKeyboardButton(text="🕹 Купить Аркадный автомат (2000 🪙)", callback_data="buy_biz_arcade")])
    else:
        # User has businesses
        kb.append([InlineKeyboardButton(text="💰 Собрать прибыль", callback_data="collect_biz")])
        
        has_manga = any(b[2] == 'manga' for b in businesses)
        has_arcade = any(b[2] == 'arcade' for b in businesses)
        
        if not has_manga:
            kb.append([InlineKeyboardButton(text="🏢 Купить Магазин Манги (500 🪙)", callback_data="buy_biz_manga")])
        if not has_arcade:
            kb.append([InlineKeyboardButton(text="🕹 Купить Аркадный автомат (2000 🪙)", callback_data="buy_biz_arcade")])
            
    kb.append([InlineKeyboardButton(text="⬅️ Назад в Экономику", callback_data="back_to_economy")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_shop_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🥤 Энергетик (150 🪙)", callback_data="shop_buy_energy")],
        [InlineKeyboardButton(text="🍜 Рамен (300 🪙)", callback_data="shop_buy_ramen")],
        [InlineKeyboardButton(text="🎫 Титул 'Семпай' (1000 🪙)", callback_data="shop_buy_title_sempai")],
        [InlineKeyboardButton(text="👑 VIP: Кастомная ИИ-Роль (5000 🪙)", callback_data="shop_buy_vip_ai")],
        [InlineKeyboardButton(text="⬅️ Назад в Экономику", callback_data="back_to_economy")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bank_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📥 Положить вклад (1000 🪙)", callback_data="bank_deposit")],
        [InlineKeyboardButton(text="📤 Снять вклад + %", callback_data="bank_withdraw")],
        [InlineKeyboardButton(text="💸 Взять кредит (500 🪙)", callback_data="bank_loan")],
        [InlineKeyboardButton(text="💳 Погасить кредит", callback_data="bank_repay")],
        [InlineKeyboardButton(text="⬅️ Назад в Экономику", callback_data="back_to_economy")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
