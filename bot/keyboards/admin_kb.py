from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🪙 Управление Коинами", callback_data="admin_coins"),
         InlineKeyboardButton(text="✨ Управление XP", callback_data="admin_xp")],
        [InlineKeyboardButton(text="💬 Чтение Истории", callback_data="admin_history")],
        [InlineKeyboardButton(text="🔐 Whitelist", callback_data="admin_whitelist_menu"),
         InlineKeyboardButton(text="🚫 Blacklist", callback_data="admin_blacklist_menu")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_whitelist_menu(status: str, count: int) -> InlineKeyboardMarkup:
    """Меню Whitelist"""
    keyboard = [
        [InlineKeyboardButton(text=f"🔐 Whitelist: {status}", callback_data="admin_toggle_whitelist")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin_whitelist_add")],
        [InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="admin_whitelist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({count})", callback_data="admin_list_whitelist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_blacklist_menu(count: int) -> InlineKeyboardMarkup:
    """Меню Blacklist"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить в Blacklist", callback_data="admin_blacklist_add")],
        [InlineKeyboardButton(text="➖ Удалить из Blacklist", callback_data="admin_blacklist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({count})", callback_data="admin_list_blacklist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Аналитика (Графики)", callback_data="admin_analytics")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export")],
        [InlineKeyboardButton(text="💻 Система", callback_data="admin_sysinfo")],
        [InlineKeyboardButton(text="📝 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="🔄 Перезагрузить", callback_data="admin_reload")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_button(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton(text="« Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
