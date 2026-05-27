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
