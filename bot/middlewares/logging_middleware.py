import logging
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger("mahiro.messages")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.text:
            logger.info(f"User {event.from_user.id} ({event.from_user.username}): {event.text}")
        return await handler(event, data)
