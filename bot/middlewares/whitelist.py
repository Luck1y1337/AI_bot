from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Callable, Dict, Any, Awaitable
from config.settings import get_settings

settings = get_settings()

class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        db = data.get("db")
        if not db:
            return await handler(event, data)
            
        user_id = event.from_user.id
        
        # Check blacklist
        blacklist_val = await db.get_setting("blacklist", "")
        blacklist = [int(x) for x in blacklist_val.split(",") if x.strip()] if blacklist_val else settings.BLACKLIST_USER_IDS
        if user_id in blacklist:
            return
            
        enable_whitelist = await db.get_setting("enable_whitelist", str(settings.ENABLE_WHITELIST).lower()) == "true"
        
        if enable_whitelist and user_id not in settings.ADMIN_USER_IDS:
            whitelist = await db.get_whitelist()
            if user_id not in whitelist:
                # User not in whitelist, send request to admins
                # Prevent spam by checking if we already sent a request recently (optional, but let's just send)
                # To prevent spam, we'll only send the request if it's a /start command
                if event.text and event.text.startswith("/start"):
                    await event.answer("🚫 Доступ ограничен.\nВаша заявка отправлена администраторам. Пожалуйста, ожидайте.")
                    
                    username = f"@{event.from_user.username}" if event.from_user.username else "Без юзернейма"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"wl_approve_{user_id}"),
                         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"wl_deny_{user_id}")]
                    ])
                    for admin_id in settings.ADMIN_USER_IDS:
                        try:
                            await event.bot.send_message(admin_id, f"📝 **Новая заявка на доступ!**\n\nID: `{user_id}`\nПользователь: {username}", reply_markup=kb)
                        except:
                            pass
                return # Block execution
                
        return await handler(event, data)
