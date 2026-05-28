from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🪙 Управление Коинами", callback_data="admin_coins"),
         InlineKeyboardButton(text="✨ Управление XP", callback_data="admin_xp")],
        [InlineKeyboardButton(text="💬 Чтение Истории", callback_data="admin_history"),
         InlineKeyboardButton(text="📜 История транзакций", callback_data="admin_transactions")],
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

def get_users_selection_kb(users: list, action: str, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура для выбора пользователя с пагинацией"""
    keyboard = []
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    
    for user in users[start_idx:end_idx]:
        display_name = f"@{user.username}" if user.username else f"ID: {user.id}"
        if action == "coin":
            text = f"{display_name} | 🪙 {user.coins}"
        elif action == "xp":
            text = f"{display_name} | ✨ {user.xp}"
        else:
            text = f"{display_name} | 💬 {user.message_count}"
        
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"admin_selectuser_{action}_{user.id}")])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_userspage_{action}_{page-1}"))
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"admin_userspage_{action}_{page+1}"))
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton(text="« Отмена", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
