# Simple declarative structures for typing
from dataclasses import dataclass

@dataclass
class User:
    id: int
    trust: int
    mood: str
    message_count: int
    xp: int
    coins: int
    is_banned: bool
    last_daily_time: float = 0.0

@dataclass
class Reminder:
    id: int
    user_id: int
    text: str
    fire_at: float

@dataclass
class Gift:
    id: int
    user_id: int
    gift_type: str

@dataclass
class Achievement:
    id: int
    user_id: int
    achievement_type: str

@dataclass
class Promocode:
    code: str
    reward_coins: int
    reward_xp: int
    max_uses: int
    current_uses: int

@dataclass
class Setting:
    key: str
    value: str
