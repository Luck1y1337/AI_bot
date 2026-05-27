from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="Статистика", callback_data="admin_stats"),
         InlineKeyboardButton(text="Аналитика", callback_data="admin_analytics")],
        [InlineKeyboardButton(text="Белый список", callback_data="admin_whitelist"),
         InlineKeyboardButton(text="Черный список", callback_data="admin_blacklist")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="Экспорт", callback_data="admin_export")],
        [InlineKeyboardButton(text="Система", callback_data="admin_sysinfo"),
         InlineKeyboardButton(text="Диагностика", callback_data="admin_diag")],
        [InlineKeyboardButton(text="Логи", callback_data="admin_logs"),
         InlineKeyboardButton(text="Перезагрузить", callback_data="admin_reload")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
