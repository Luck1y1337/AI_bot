import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger("mahiro.messages")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            if event.text:
                logger.info(f"User {event.from_user.id} ({event.from_user.username}): {event.text}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"User {event.from_user.id} ({event.from_user.username}) [callback]: {event.data}")
        return await handler(event, data)
