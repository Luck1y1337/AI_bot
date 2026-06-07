import asyncio
from database.repository import Database
from bot.handlers.economy_handler import cb_eco_contracts

class MockUser:
    id = 123456789

class MockCallback:
    from_user = MockUser()
    data = "eco_contracts"
    
    class Message:
        async def edit_text(self, text, reply_markup=None, parse_mode=None):
            print("EDIT TEXT:", text)
            print("PARSE MODE:", parse_mode)
            print("MARKUP:", reply_markup.inline_keyboard if reply_markup else None)
    
    message = Message()
    
    async def answer(self, text, show_alert=False):
        print("ANSWER:", text)

async def test():
    db = Database()
    await db.connect()
    # Create user
    await db.get_user(MockCallback.from_user.id)
    
    try:
        await cb_eco_contracts(MockCallback(), db)
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
