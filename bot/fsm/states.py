from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_whitelist = State()
    waiting_for_blacklist = State()
    waiting_for_unblacklist = State()
    waiting_for_broadcast = State()
    waiting_for_coin_user_id = State()
    waiting_for_coin_amount = State()
    waiting_for_xp_user_id = State()
    waiting_for_xp_amount = State()
    waiting_for_history_user_id = State()
    waiting_for_reply_text = State()
    waiting_for_promo_data = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()

class SupportStates(StatesGroup):
    waiting_for_ticket = State()
    waiting_for_reply = State()

class PayStates(StatesGroup):
    waiting_for_user = State()
    waiting_for_amount = State()

class CasinoStates(StatesGroup):
    waiting_for_opponent = State()
    waiting_for_bet = State()

class MarryStates(StatesGroup):
    waiting_for_partner = State()

class RepStates(StatesGroup):
    waiting_for_target = State()

class ShopStates(StatesGroup):
    waiting_for_custom_prompt = State()

class MarketStates(StatesGroup):
    waiting_for_sell_price = State()

class VoiceStates(StatesGroup):
    waiting_for_text = State()

class RemindStates(StatesGroup):
    waiting_for_input = State()

class PromoStates(StatesGroup):
    waiting_for_code = State()

class ClanStates(StatesGroup):
    waiting_for_clan_name = State()
    waiting_for_donate = State()
    waiting_for_join_name = State()
    waiting_for_kick_user = State()

class BlackjackStates(StatesGroup):
    waiting_for_bet = State()
    playing = State()

class RouletteStates(StatesGroup):
    waiting_for_bet = State()

class AIGamesStates(StatesGroup):
    playing_guess_number = State()
    playing_words = State()
