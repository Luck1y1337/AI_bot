from aiogram import BaseMiddleware
from aiogram.types import Message
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
        user_id = event.from_user.id
        if settings.ENABLE_WHITELIST and user_id not in settings.WHITELIST_USER_IDS and user_id not in settings.ADMIN_USER_IDS:
            return # Ignore
        if user_id in settings.BLACKLIST_USER_IDS:
            return # Ignore
        return await handler(event, data)
