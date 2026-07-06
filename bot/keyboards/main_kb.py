from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import get_settings

def get_main_menu(user_id: int = 0) -> ReplyKeyboardMarkup:
    # A single persistent launcher — everything else lives in the inline hub.
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="☰ Меню")]],
        resize_keyboard=True,
        is_persistent=True,
    )

# Header shown above the main inline hub.
HUB_HEADER = (
    "🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n"
    "━━━━━━━━━━━━━━\n"
    "Выбери раздел 👇"
)

def get_main_hub(user_id: int = 0) -> InlineKeyboardMarkup:
    settings = get_settings()
    kb = [
        [InlineKeyboardButton(text="🎮 Игры", callback_data="cat_games"),
         InlineKeyboardButton(text="💼 Заработок", callback_data="cat_income")],
        [InlineKeyboardButton(text="🤝 Социальное", callback_data="cat_social"),
         InlineKeyboardButton(text="🐾 Питомец", callback_data="eco_pets")],
        [InlineKeyboardButton(text="📅 Ежедневный бонус", callback_data="eco_daily")],
        [InlineKeyboardButton(text="📊 Профиль", callback_data="open_stats"),
         InlineKeyboardButton(text="🏆 Лидеры", callback_data="open_leaderboard")],
        [InlineKeyboardButton(text="🎁 Промокод", callback_data="open_promo"),
         InlineKeyboardButton(text="🎤 Голос", callback_data="open_voice")],
        [InlineKeyboardButton(text="💝 Поддержать", callback_data="open_donate"),
         InlineKeyboardButton(text="🆘 Поддержка", callback_data="open_support")],
        [InlineKeyboardButton(text="🔗 Пригласить друга", callback_data="open_invite")],
    ]
    if user_id in settings.ADMIN_USER_IDS:
        kb.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="open_admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_pay_users_kb(users: list, page: int = 0) -> InlineKeyboardMarkup:
    keyboard = []
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_users = users[start_idx:end_idx]
    
    for user in current_users:
        display_name = f"@{user.username}" if user.username else f"ID: {user.id}"
        keyboard.append([InlineKeyboardButton(
            text=f"{display_name} | Баланс: {user.coins} 🪙", 
            callback_data=f"pay_select_{user.id}"
        )])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pay_page_{page-1}"))
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"pay_page_{page+1}"))
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_social_users_kb(users: list, page: int = 0) -> InlineKeyboardMarkup:
    from utils.levels import get_level
    keyboard = []
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_users = users[start_idx:end_idx]

    for user in current_users:
        display_name = f"@{user.username}" if user.username else f"ID: {user.id}"
        keyboard.append([InlineKeyboardButton(
            text=f"👤 {display_name} | Ур. {get_level(user.xp)}",
            callback_data=f"pay_select_{user.id}"
        )])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="« Назад", callback_data=f"pay_page_{page-1}"))
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton(text="Вперед »", callback_data=f"pay_page_{page+1}"))
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton(text="× Отмена", callback_data="pay_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_eco_games_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎰 Казино (Coinflip)", callback_data="eco_casino"),
         InlineKeyboardButton(text="🔫 Рулетка", callback_data="roul_main")],
        [InlineKeyboardButton(text="🃏 Блэкджек (21)", callback_data="eco_blackjack"),
         InlineKeyboardButton(text="🎰 Слоты", callback_data="eco_slots")],
        [InlineKeyboardButton(text="✌️ Камень-Ножницы", callback_data="rps_main"),
         InlineKeyboardButton(text="🤖 Игры с ИИ", callback_data="ai_games_menu")],
        [InlineKeyboardButton(text="🎴 Гача (Карточки)", callback_data="gacha_menu"),
         InlineKeyboardButton(text="🔮 Подземелье", callback_data="eco_dungeon")],
        [InlineKeyboardButton(text="🐾 Тамагочи", callback_data="eco_pets"),
         InlineKeyboardButton(text="🎮 Викторина", callback_data="eco_quiz")],
        [InlineKeyboardButton(text="⚔️ Рейд на Босса", callback_data="eco_raid"),
         InlineKeyboardButton(text="🎟 Лотерея", callback_data="eco_lottery")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_hub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_eco_income_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💼 Мои Бизнесы", callback_data="eco_businesses"),
         InlineKeyboardButton(text="🏦 Банк Махиро", callback_data="eco_bank")],
        [InlineKeyboardButton(text="🎯 Контракты (Квесты)", callback_data="eco_contracts"),
         InlineKeyboardButton(text="🏪 Магазин", callback_data="eco_shop")],
        [InlineKeyboardButton(text="🛒 Глобальный Рынок", callback_data="eco_market")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_hub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_eco_social_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🏰 Кланы", callback_data="eco_clans"),
         InlineKeyboardButton(text="💍 Предложить Брак", callback_data="eco_marry")],
        [InlineKeyboardButton(text="🎯 Доска Наград", callback_data="eco_bounties"),
         InlineKeyboardButton(text="🤝 Трейд (Предметы)", callback_data="eco_trade")],
        [InlineKeyboardButton(text="💸 Перевод Коинов", callback_data="eco_transfer"),
         InlineKeyboardButton(text="👍 +Репутация", callback_data="eco_rep")],
        [InlineKeyboardButton(text="🎁 Подарить ИИ Подарок", callback_data="gift_main")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_hub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_stats_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="⏰ Мои Напоминания", callback_data="stats_reminders")],
        [InlineKeyboardButton(text="🔄 Сброс памяти ИИ (Reset)", callback_data="stats_reset")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_hub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

