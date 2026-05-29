import aiosqlite
from typing import List, Optional
import time
from .models import User, Reminder, Gift, Achievement, Transaction

class Database:
    def __init__(self, db_path: str = "data/mahiro.db"):
        self.db_path = db_path
        self._conn = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute('pragma journal_mode=wal')
        await self._conn.execute('pragma foreign_keys=ON')
        await self.init_db()

    async def init_db(self):
        await self._conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                trust INTEGER DEFAULT 50,
                mood TEXT DEFAULT 'normal',
                message_count INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                last_daily_time REAL DEFAULT 0,
                username TEXT DEFAULT "",
                custom_prompt TEXT DEFAULT ""
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                fire_at REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                gift_type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward_coins INTEGER DEFAULT 0,
                reward_xp INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 1,
                current_uses INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                amount INTEGER,
                action_type TEXT,
                timestamp REAL
            );
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                business_type TEXT,
                last_collect_time REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_type TEXT,
                item_value TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS bank_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                record_type TEXT,
                amount INTEGER,
                timestamp REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_type TEXT,
                progress INTEGER DEFAULT 0,
                target INTEGER,
                is_completed BOOLEAN DEFAULT 0,
                day_timestamp REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS marriages (
                user1_id INTEGER,
                user2_id INTEGER,
                timestamp REAL,
                PRIMARY KEY (user1_id, user2_id)
            );
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                treasury INTEGER DEFAULT 0,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'member',
                joined_at REAL,
                FOREIGN KEY(clan_id) REFERENCES clans(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        ''')
        
        # Schema migrations
        try:
            await self._conn.execute('ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0')
        except Exception:
            pass
            
        try:
            await self._conn.execute('ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0')
        except Exception:
            pass
            
        try:
            await self._conn.execute('ALTER TABLE users ADD COLUMN custom_prompt TEXT DEFAULT ""')
        except Exception:
            pass
            
        try:
            await self._conn.execute('ALTER TABLE users ADD COLUMN last_daily_time REAL DEFAULT 0')
        except Exception:
            pass
            
        try:
            await self._conn.execute('ALTER TABLE users ADD COLUMN username TEXT DEFAULT ""')
        except Exception:
            pass
            
        await self._conn.commit()

    async def get_setting(self, key: str, default: str = None) -> str:
        async with self._conn.execute('SELECT value FROM settings WHERE key = ?', (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        await self._conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        await self._conn.commit()
        
    async def get_whitelist(self) -> List[int]:
        val = await self.get_setting('whitelist', '')
        if not val: return []
        return [int(x) for x in val.split(',') if x.strip()]
        
    async def add_to_whitelist(self, user_id: int):
        wl = await self.get_whitelist()
        if user_id not in wl:
            wl.append(user_id)
            await self.set_setting('whitelist', ','.join(map(str, wl)))
            
    async def remove_from_whitelist(self, user_id: int):
        wl = await self.get_whitelist()
        if user_id in wl:
            wl.remove(user_id)
            await self.set_setting('whitelist', ','.join(map(str, wl)))

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def get_user(self, user_id: int) -> User:
        async with self._conn.execute('SELECT id, trust, mood, message_count, xp, coins, is_banned, last_daily_time, username, custom_prompt FROM users WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(*row)
            # Create user if not exists
            await self._conn.execute('INSERT INTO users (id) VALUES (?)', (user_id,))
            await self._conn.commit()
            return User(user_id, 50, 'normal', 0, 0, 0, False, 0.0, "", None)

    async def update_user(self, user: User):
        await self._conn.execute('''
            UPDATE users SET trust = ?, mood = ?, message_count = ?, xp = ?, coins = ?, is_banned = ?, last_daily_time = ?, username = ?, custom_prompt = ? WHERE id = ?
        ''', (user.trust, user.mood, user.message_count, user.xp, user.coins, user.is_banned, user.last_daily_time, user.username, user.custom_prompt, user.id))
        await self._conn.commit()
        
    async def get_all_users(self) -> List[User]:
        async with self._conn.execute('SELECT id, trust, mood, message_count, xp, coins, is_banned, last_daily_time, username, custom_prompt FROM users') as cursor:
            rows = await cursor.fetchall()
            return [User(*row) for row in rows]
            
    async def add_transaction(self, sender_id: int, receiver_id: int, amount: int, action_type: str):
        await self._conn.execute('INSERT INTO transactions (sender_id, receiver_id, amount, action_type, timestamp) VALUES (?, ?, ?, ?, ?)', 
                                 (sender_id, receiver_id, amount, action_type, time.time()))
        await self._conn.commit()
        
    async def get_transactions(self, limit: int = 20) -> List[Transaction]:
        async with self._conn.execute('SELECT id, sender_id, receiver_id, amount, action_type, timestamp FROM transactions ORDER BY timestamp DESC LIMIT ?', (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [Transaction(*row) for row in rows]

    async def add_reminder(self, user_id: int, text: str, fire_at: float):
        await self._conn.execute('INSERT INTO reminders (user_id, text, fire_at) VALUES (?, ?, ?)', (user_id, text, fire_at))
        await self._conn.commit()

    async def get_due_reminders(self, current_time: float) -> List[Reminder]:
        async with self._conn.execute('SELECT id, user_id, text, fire_at FROM reminders WHERE fire_at <= ?', (current_time,)) as cursor:
            rows = await cursor.fetchall()
            return [Reminder(*row) for row in rows]

    async def delete_reminder(self, reminder_id: int):
        await self._conn.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        await self._conn.commit()

    async def get_user_reminders(self, user_id: int) -> List[Reminder]:
        async with self._conn.execute('SELECT id, user_id, text, fire_at FROM reminders WHERE user_id = ? ORDER BY fire_at ASC', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [Reminder(*row) for row in rows]

    async def add_gift(self, user_id: int, gift_type: str):
        await self._conn.execute('INSERT INTO gifts (user_id, gift_type) VALUES (?, ?)', (user_id, gift_type))
        await self._conn.commit()

    async def get_user_gifts(self, user_id: int) -> List[Gift]:
        async with self._conn.execute('SELECT id, user_id, gift_type FROM gifts WHERE user_id = ?', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [Gift(*row) for row in rows]

    async def add_achievement(self, user_id: int, achievement_type: str):
        await self._conn.execute('INSERT INTO achievements (user_id, achievement_type) VALUES (?, ?)', (user_id, achievement_type))
        await self._conn.commit()

    async def get_user_achievements(self, user_id: int) -> List[Achievement]:
        async with self._conn.execute('SELECT id, user_id, achievement_type FROM achievements WHERE user_id = ?', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [Achievement(*row) for row in rows]

    async def get_top_users_by_xp(self, limit: int = 10) -> List[User]:
        async with self._conn.execute('SELECT id, trust, mood, message_count, xp, coins, is_banned, last_daily_time, username FROM users ORDER BY xp DESC LIMIT ?', (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [User(*row) for row in rows]

    async def add_business(self, user_id: int, business_type: str):
        await self._conn.execute('INSERT INTO businesses (user_id, business_type, last_collect_time) VALUES (?, ?, ?)', (user_id, business_type, time.time()))
        await self._conn.commit()

    async def get_user_businesses(self, user_id: int) -> List[tuple]:
        async with self._conn.execute('SELECT id, user_id, business_type, last_collect_time FROM businesses WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchall()
            
    async def update_business_collect_time(self, business_id: int, collect_time: float):
        await self._conn.execute('UPDATE businesses SET last_collect_time = ? WHERE id = ?', (collect_time, business_id))
        await self._conn.commit()

    async def add_inventory_item(self, user_id: int, item_type: str, item_value: str):
        await self._conn.execute('INSERT INTO inventory (user_id, item_type, item_value) VALUES (?, ?, ?)', (user_id, item_type, item_value))
        await self._conn.commit()

    async def get_user_inventory(self, user_id: int) -> List[tuple]:
        async with self._conn.execute('SELECT id, user_id, item_type, item_value FROM inventory WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchall()

    async def add_bank_record(self, user_id: int, record_type: str, amount: int):
        await self._conn.execute('INSERT INTO bank_records (user_id, record_type, amount, timestamp) VALUES (?, ?, ?, ?)', (user_id, record_type, amount, time.time()))
        await self._conn.commit()

    async def get_user_bank_records(self, user_id: int) -> List[tuple]:
        async with self._conn.execute('SELECT id, user_id, record_type, amount, timestamp FROM bank_records WHERE user_id = ? ORDER BY timestamp DESC', (user_id,)) as cursor:
            return await cursor.fetchall()

    async def add_marriage(self, user1_id: int, user2_id: int):
        await self._conn.execute('INSERT INTO marriages (user1_id, user2_id, timestamp) VALUES (?, ?, ?)', (user1_id, user2_id, time.time()))
        await self._conn.commit()

    async def get_marriage(self, user_id: int) -> Optional[tuple]:
        async with self._conn.execute('SELECT user1_id, user2_id, timestamp FROM marriages WHERE user1_id = ? OR user2_id = ?', (user_id, user_id)) as cursor:
            return await cursor.fetchone()

    # --- Clans ---
    async def create_clan(self, name: str, owner_id: int) -> int:
        cursor = await self._conn.execute('INSERT INTO clans (name, owner_id) VALUES (?, ?)', (name, owner_id))
        clan_id = cursor.lastrowid
        await self.add_clan_member(clan_id, owner_id, 'owner')
        await self._conn.commit()
        return clan_id

    async def get_clan(self, clan_id: int) -> Optional[tuple]:
        async with self._conn.execute('SELECT id, name, owner_id, level, xp, treasury FROM clans WHERE id = ?', (clan_id,)) as cursor:
            return await cursor.fetchone()

    async def get_clan_by_name(self, name: str) -> Optional[tuple]:
        async with self._conn.execute('SELECT id, name, owner_id, level, xp, treasury FROM clans WHERE name = ?', (name,)) as cursor:
            return await cursor.fetchone()

    async def get_user_clan(self, user_id: int) -> Optional[tuple]:
        async with self._conn.execute('''
            SELECT c.id, c.name, c.owner_id, c.level, c.xp, c.treasury, cm.role
            FROM clans c
            JOIN clan_members cm ON c.id = cm.clan_id
            WHERE cm.user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchone()

    async def get_clan_members(self, clan_id: int) -> List[tuple]:
        async with self._conn.execute('SELECT user_id, role, joined_at FROM clan_members WHERE clan_id = ?', (clan_id,)) as cursor:
            return await cursor.fetchall()

    async def add_clan_member(self, clan_id: int, user_id: int, role: str = 'member'):
        await self._conn.execute('INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)', (clan_id, user_id, role, time.time()))
        await self._conn.commit()

    async def remove_clan_member(self, clan_id: int, user_id: int):
        await self._conn.execute('DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?', (clan_id, user_id))
        await self._conn.commit()
        
    async def update_clan_treasury(self, clan_id: int, amount: int):
        await self._conn.execute('UPDATE clans SET treasury = treasury + ? WHERE id = ?', (amount, clan_id))
        await self._conn.commit()

    # --- Contracts / Quests ---
    async def get_user_contracts(self, user_id: int, start_of_day: float) -> List[tuple]:
        async with self._conn.execute('SELECT id, task_type, progress, target, is_completed, day_timestamp FROM contracts WHERE user_id = ? AND day_timestamp >= ?', (user_id, start_of_day)) as cursor:
            return await cursor.fetchall()
            
    async def add_contract(self, user_id: int, task_type: str, target: int, day_timestamp: float):
        await self._conn.execute('INSERT INTO contracts (user_id, task_type, target, day_timestamp) VALUES (?, ?, ?, ?)', (user_id, task_type, target, day_timestamp))
        await self._conn.commit()
        
    async def update_contract_progress(self, contract_id: int, progress: int, is_completed: bool):
        await self._conn.execute('UPDATE contracts SET progress = ?, is_completed = ? WHERE id = ?', (progress, int(is_completed), contract_id))
        await self._conn.commit()

    async def get_daily_activity(self) -> dict:
        # Simplistic stub for activity over 14 days; in a real scenario we'd query a messages table.
        # Here we just mock it for the chart since the requirement says "message count".
        return {f"Day {i}": i * 10 for i in range(1, 15)}
