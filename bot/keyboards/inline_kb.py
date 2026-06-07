from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_gifts_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="Снек 🍫 (50 🪙)", callback_data="gift_snack"),
         InlineKeyboardButton(text="Игрушка 🧸 (150 🪙)", callback_data="gift_plushie")],
        [InlineKeyboardButton(text="Игра 🎮 (300 🪙)", callback_data="gift_game"),
         InlineKeyboardButton(text="Мерч 🖼 (500 🪙)", callback_data="gift_merch")],
        [InlineKeyboardButton(text="Ранобэ 📚 (100 🪙)", callback_data="gift_lnovel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_quiz_kb(options: list, correct_idx: int) -> InlineKeyboardMarkup:
    kb = []
    for i, opt in enumerate(options):
        is_correct = "1" if i == correct_idx else "0"
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"quiz_{is_correct}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_blackjack_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="Взять карту 🃏", callback_data="bj_hit")],
        [InlineKeyboardButton(text="Хватит 🛑", callback_data="bj_stand")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_roulette_bet_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="10 🪙", callback_data="rl_bet_10"),
         InlineKeyboardButton(text="50 🪙", callback_data="rl_bet_50"),
         InlineKeyboardButton(text="100 🪙", callback_data="rl_bet_100")],
        [InlineKeyboardButton(text="500 🪙", callback_data="rl_bet_500"),
         InlineKeyboardButton(text="1000 🪙", callback_data="rl_bet_1000")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_economy")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_roulette_color_kb(bet: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="Красное 🔴 (x2)", callback_data=f"rl_color_{bet}_red")],
        [InlineKeyboardButton(text="Черное ⚫ (x2)", callback_data=f"rl_color_{bet}_black")],
        [InlineKeyboardButton(text="Зеленое 🟢 (x14)", callback_data=f"rl_color_{bet}_green")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_economy")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
