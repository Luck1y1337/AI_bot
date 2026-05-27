from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config.settings import get_settings

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    settings = get_settings()
    
    kb = [
        [KeyboardButton(text="🎮 Играть (Quiz)"), KeyboardButton(text="🎁 Подарить")],
        [KeyboardButton(text="📊 Моя Статистика"), KeyboardButton(text="🏆 Лидеры")],
        [KeyboardButton(text="⏰ Мои Напоминания"), KeyboardButton(text="🎤 Голос")],
        [KeyboardButton(text="🆘 Поддержка"), KeyboardButton(text="💝 Поддержать проект")]
    ]
    
    if user_id in settings.ADMIN_USER_IDS:
        kb.append([KeyboardButton(text="👑 Админ Панель")])
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, is_persistent=False)
