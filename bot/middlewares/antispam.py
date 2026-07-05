import time
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict
from config.settings import get_settings

settings = get_settings()

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_message = defaultdict(float)
        self.flood_history = defaultdict(list)
        self.muted_until = defaultdict(float)
        self.last_callback = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if user_id in settings.ADMIN_USER_IDS:
            return await handler(event, data)

        now = time.time()

        # A muted user is blocked from both messages and callbacks.
        if now < self.muted_until[user_id]:
            if isinstance(event, CallbackQuery):
                await event.answer("Хватит спамить! Я тебя пока игнорирую. 💤", show_alert=True)
            return

        # Callbacks get a light throttle only (no flood escalation) so menu
        # navigation stays smooth while rapid-fire abuse is still curbed.
        if isinstance(event, CallbackQuery):
            if now - self.last_callback[user_id] < 0.7:
                await event.answer()
                return
            self.last_callback[user_id] = now
            return await handler(event, data)

        # Message cooldown (2 seconds)
        if now - self.last_message[user_id] < 2.0:
            return

        self.last_message[user_id] = now

        # Flood protection (5 msgs in 10s -> 60s mute)
        self.flood_history[user_id].append(now)
        self.flood_history[user_id] = [t for t in self.flood_history[user_id] if now - t < 10.0]

        if len(self.flood_history[user_id]) >= 5:
            self.muted_until[user_id] = now + 60.0
            db = data['db']
            user = await db.get_user(user_id)
            user.trust -= 10
            await db.update_user(user)

            # Award spammer achievement
            current_achs = [a.achievement_type for a in await db.get_user_achievements(user_id)]
            if "spammer" not in current_achs:
                await db.add_achievement(user_id, "spammer")
                await event.answer("Эм... ты пишешь слишком быстро! Хватит спамить! (Открыто достижение: Спамер)")
            else:
                await event.answer("Эм... хватит спамить! Я тебя пока игнорирую.")

            bot = data.get('bot')
            if bot:
                from utils.admin_alerts import notify_admins
                await notify_admins(bot, f"Spam detected from User {user_id}. Muted for 60s.")
            return

        return await handler(event, data)
