from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_whitelist = State()
    waiting_for_blacklist = State()
    waiting_for_unblacklist = State()
    waiting_for_broadcast = State()

class SupportStates(StatesGroup):
    waiting_for_ticket = State()
    waiting_for_reply = State()
