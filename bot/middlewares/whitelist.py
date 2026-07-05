from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.text_decorations import html_decoration
from typing import Callable, Dict, Any, Awaitable
from config.settings import get_settings

settings = get_settings()

class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        db = data.get("db")
        if not db:
            return await handler(event, data)

        user_id = event.from_user.id

        # Banned users are blocked everywhere (messages and callbacks).
        # users.is_banned is the single source of truth.
        if user_id not in settings.ADMIN_USER_IDS and await db.is_user_banned(user_id):
            if isinstance(event, CallbackQuery):
                await event.answer("🚫 Вы заблокированы.", show_alert=True)
            return

        enable_whitelist = await db.get_setting("enable_whitelist", str(settings.ENABLE_WHITELIST).lower()) == "true"

        if enable_whitelist and user_id not in settings.ADMIN_USER_IDS:
            whitelist = await db.get_whitelist()
            if user_id not in whitelist:
                # Only message /start creates an access request; callbacks are just blocked.
                if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                    await event.answer("🚫 Доступ ограничен.\nВаша заявка отправлена администраторам. Пожалуйста, ожидайте.")

                    username = f"@{html_decoration.quote(event.from_user.username)}" if event.from_user.username else "Без юзернейма"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"wl_approve_{user_id}"),
                         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"wl_deny_{user_id}")]
                    ])
                    for admin_id in settings.ADMIN_USER_IDS:
                        try:
                            await event.bot.send_message(admin_id, f"📝 <b>Новая заявка на доступ!</b>\n\nID: <code>{user_id}</code>\nПользователь: {username}", reply_markup=kb)
                        except Exception:
                            pass
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Доступ ограничен.", show_alert=True)
                return  # Block execution

        return await handler(event, data)
