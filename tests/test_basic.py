import pytest
from database.repository import Database
import asyncio
import os

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()

@pytest.mark.asyncio
async def test_user_creation(db):
    user = await db.get_user(123)
    assert user.id == 123
    assert user.trust == 50
    assert user.mood == "normal"
    assert user.message_count == 0

@pytest.mark.asyncio
async def test_trust_update(db):
    user = await db.get_user(123)
    user.trust = 80
    await db.update_user(user)
    updated = await db.get_user(123)
    assert updated.trust == 80

@pytest.mark.asyncio
async def test_reminders(db):
    await db.add_reminder(123, "test", 1000.0)
    reminders = await db.get_user_reminders(123)
    assert len(reminders) == 1
    assert reminders[0].text == "test"
