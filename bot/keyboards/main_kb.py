from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import get_settings

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    settings = get_settings()
    
    kb = [
        [KeyboardButton(text="🌟 Интерактив и Экономика")],
        [KeyboardButton(text="📊 Моя Статистика"), KeyboardButton(text="🏆 Лидеры")],
        [KeyboardButton(text="⏰ Мои Напоминания"), KeyboardButton(text="🎤 Голос")],
        [KeyboardButton(text="🐾 Мой Питомец"), KeyboardButton(text="🆘 Поддержка")]
    ]
    
    if user_id in settings.ADMIN_USER_IDS:
        kb.append([KeyboardButton(text="👑 Админ Панель")])
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, is_persistent=False)

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

def get_economy_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📅 Ежедневный Бонус", callback_data="eco_daily"),
         InlineKeyboardButton(text="🎯 Контракты (Квесты)", callback_data="eco_contracts")],
        [InlineKeyboardButton(text="💼 Мои Бизнесы", callback_data="eco_businesses"),
         InlineKeyboardButton(text="🏪 Магазин", callback_data="eco_shop")],
        [InlineKeyboardButton(text="🏦 Банк Махиро", callback_data="eco_bank"),
         InlineKeyboardButton(text="🎰 Казино (Coinflip)", callback_data="eco_casino")],
        [InlineKeyboardButton(text="💸 Перевод Коинов", callback_data="eco_transfer"),
         InlineKeyboardButton(text="🎰 Гача (Карточки)", callback_data="gacha_menu")],
        [InlineKeyboardButton(text="🛒 Глобальный Рынок", callback_data="eco_market"),
         InlineKeyboardButton(text="⚔️ Рейд на Босса", callback_data="eco_raid")],
        [InlineKeyboardButton(text="💍 Предложить Брак", callback_data="eco_marry"),
         InlineKeyboardButton(text="👍 +Репутация", callback_data="eco_rep")],
        [InlineKeyboardButton(text="🎮 Викторина (Quiz)", callback_data="eco_quiz"),
         InlineKeyboardButton(text="🏰 Кланы", callback_data="eco_clans")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
