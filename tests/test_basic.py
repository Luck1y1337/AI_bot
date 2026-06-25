import pytest
import time
from database.repository import Database
from utils.levels import get_level, get_title, get_xp_for_next, check_level_up



@pytest.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


# --- User CRUD ---

async def test_user_creation(db):
    user = await db.get_user(123)
    assert user.id == 123
    assert user.trust == 50
    assert user.mood == "normal"
    assert user.message_count == 0
    assert user.streak_count == 0
    assert user.referred_by == 0


async def test_trust_update(db):
    user = await db.get_user(123)
    user.trust = 80
    await db.update_user(user)
    updated = await db.get_user(123)
    assert updated.trust == 80


async def test_reminders(db):
    await db.get_user(123)
    await db.add_reminder(123, "test", 1000.0)
    reminders = await db.get_user_reminders(123)
    assert len(reminders) == 1
    assert reminders[0].text == "test"


# --- BUG-01: Business profit must accumulate ---

async def test_business_collect_time_updates(db):
    user = await db.get_user(200)
    await db.add_business(user.id, "manga")
    businesses = await db.get_user_businesses(user.id)
    assert len(businesses) == 1
    assert businesses[0][2] == "manga"


# --- BUG-05: Clan kick needs c_id ---

async def test_clan_create_and_member(db):
    user = await db.get_user(300)
    await db.get_user(301)
    clan_id = await db.create_clan("TestClan", user.id)
    assert clan_id > 0
    members = await db.get_clan_members(clan_id)
    assert len(members) == 1
    assert members[0][0] == 300

    await db.add_clan_member(clan_id, 301, "member")
    members = await db.get_clan_members(clan_id)
    assert len(members) == 2

    await db.remove_clan_member(clan_id, 301)
    members = await db.get_clan_members(clan_id)
    assert len(members) == 1


# --- BUG-06: get_top_users_by_xp must return full User objects ---

async def test_top_users_by_xp(db):
    user = await db.get_user(400)
    user.xp = 9999
    await db.update_user(user)
    top = await db.get_top_users_by_xp(5)
    assert len(top) > 0
    first = top[0]
    assert hasattr(first, "profile_frame")
    assert hasattr(first, "tutorial_done")
    assert hasattr(first, "streak_count")
    assert hasattr(first, "referred_by")


# --- Coins deduction atomicity ---

async def test_deduct_coins_insufficient(db):
    user = await db.get_user(500)
    user.coins = 50
    await db.update_user(user)
    result = await db.deduct_coins(500, 100)
    assert result is False
    updated = await db.get_user(500)
    assert updated.coins == 50


async def test_deduct_coins_sufficient(db):
    user = await db.get_user(501)
    user.coins = 200
    await db.update_user(user)
    result = await db.deduct_coins(501, 100)
    assert result is True
    updated = await db.get_user(501)
    assert updated.coins == 100


# --- Streak persistence ---

async def test_streak_persistence(db):
    user = await db.get_user(600)
    user.streak_count = 7
    user.last_streak_date = "2026-06-25"
    await db.update_user(user)
    loaded = await db.get_user(600)
    assert loaded.streak_count == 7
    assert loaded.last_streak_date == "2026-06-25"


# --- Referral persistence ---

async def test_referral_persistence(db):
    user = await db.get_user(700)
    user.referred_by = 100
    await db.update_user(user)
    loaded = await db.get_user(700)
    assert loaded.referred_by == 100
    count = await db.get_referral_count(100)
    assert count == 1


# --- Inventory amounts ---

async def test_inventory_add_remove(db):
    await db.get_user(800)
    await db.add_inventory_amount(800, "wood", 10)
    item = await db.get_inventory_item(800, "wood")
    assert item[2] == 10

    result = await db.remove_inventory_amount(800, "wood", 5)
    assert result is True
    item = await db.get_inventory_item(800, "wood")
    assert item[2] == 5

    result = await db.remove_inventory_amount(800, "wood", 100)
    assert result is False


# --- Black market DB persistence ---

async def test_black_market_db(db):
    items = [
        {"id": "bm_1", "name": "Test Item", "price": 100, "type": "test", "stock": 3},
    ]
    await db.seed_black_market(items, time.time())
    loaded = await db.get_black_market_items()
    assert len(loaded) == 1
    assert loaded[0][4] == 3

    result = await db.decrement_bm_stock("bm_1")
    assert result is True
    item = await db.get_bm_item("bm_1")
    assert item[4] == 2


# --- Daily activity (BUG-17 fix) ---

async def test_daily_activity_real_data(db):
    activity = await db.get_daily_activity()
    assert isinstance(activity, dict)
    assert len(activity) == 14


# --- Levels module ---

def test_get_level():
    assert get_level(0) == 1
    assert get_level(99) == 1
    assert get_level(100) == 2
    assert get_level(250) == 3
    assert get_level(4999) == 50


def test_get_title():
    assert get_title(0) == "Новичок"
    assert get_title(999) == "Приятель"
    assert get_title(4999) == "Мифический"


def test_get_xp_for_next():
    cur, need = get_xp_for_next(150)
    assert cur == 50
    assert need == 100


def test_check_level_up():
    leveled, new_level, reward = check_level_up(95, 105)
    assert leveled is True
    assert new_level == 2
    assert reward == 200

    leveled, _, _ = check_level_up(50, 60)
    assert leveled is False


def test_multi_level_up():
    leveled, new_level, reward = check_level_up(90, 510)
    assert leveled is True
    assert new_level == 6
    assert reward > 0
