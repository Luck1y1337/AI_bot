from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import get_settings

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    settings = get_settings()
    
    kb = [
        [KeyboardButton(text="🎮 Играть (Quiz)"), KeyboardButton(text="🎁 Подарить")],
        [KeyboardButton(text="📅 Ежедневный Бонус"), KeyboardButton(text="🎰 Гача-бокс")],
        [KeyboardButton(text="💸 Перевести"), KeyboardButton(text="📊 Моя Статистика")],
        [KeyboardButton(text="🏆 Лидеры"), KeyboardButton(text="⏰ Мои Напоминания")],
        [KeyboardButton(text="🎤 Голос"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="💝 Поддержать проект")]
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
