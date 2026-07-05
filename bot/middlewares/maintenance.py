from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config.settings import get_settings

settings = get_settings()

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        db = data.get('db')
        if db:
            async with db._conn.execute('SELECT value FROM settings WHERE key = ?', ('maintenance',)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 'true':
                    if event.from_user.id not in settings.ADMIN_USER_IDS:
                        text = "Махиро сейчас спит... (Техническое обслуживание). Приходи позже! Zzz 💤"
                        if isinstance(event, CallbackQuery):
                            await event.answer(text, show_alert=True)
                        else:
                            await event.answer(text)
                        return

        return await handler(event, data)
