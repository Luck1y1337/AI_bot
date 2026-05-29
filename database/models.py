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
    username: str = ""
    custom_prompt: str = None

@dataclass
class Transaction:
    id: int
    sender_id: int
    receiver_id: int
    amount: int
    action_type: str
    timestamp: float

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
class Business:
    id: int
    user_id: int
    business_type: str
    last_collect_time: float

@dataclass
class InventoryItem:
    id: int
    user_id: int
    item_type: str
    item_value: str

@dataclass
class BankRecord:
    id: int
    user_id: int
    record_type: str # 'deposit' or 'loan'
    amount: int
    timestamp: float

@dataclass
class Contract:
    id: int
    user_id: int
    task_type: str
    progress: int
    target: int
    is_completed: bool
    day_timestamp: float
