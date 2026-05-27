from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from config.settings import get_settings

settings = get_settings()

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Check if settings has maintenance mode (mocking it using a global or env for now)
        # For simplicity, we can rely on a class-level variable in settings or a db table
        db = data.get('db')
        if db:
            async with db._conn.execute('SELECT value FROM settings WHERE key = ?', ('maintenance',)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 'true':
                    if event.from_user.id not in settings.ADMIN_USER_IDS:
                        await event.answer("Махиро сейчас спит... (Техническое обслуживание). Приходи позже! Zzz 💤")
                        return

        return await handler(event, data)
