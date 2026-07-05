from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import asyncio

router = Router()

SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
PAYOUTS = {
    ("7️⃣", "7️⃣", "7️⃣"): 50,
    ("💎", "💎", "💎"): 25,
    ("⭐", "⭐", "⭐"): 15,
    ("🔔", "🔔", "🔔"): 10,
    ("🍋", "🍋", "🍋"): 5,
    ("🍒", "🍒", "🍒"): 3,
}

WEIGHTS = [30, 25, 20, 15, 7, 3]


def get_slots_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎰 Крутить (50 🪙)", callback_data="slots_spin_50"),
         InlineKeyboardButton(text="🎰 Крутить (200 🪙)", callback_data="slots_spin_200")],
        [InlineKeyboardButton(text="🎰 Крутить (1000 🪙)", callback_data="slots_spin_1000")],
        [InlineKeyboardButton(text="🔙 Назад в Игры", callback_data="cat_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.callback_query(F.data == "eco_slots")
async def cb_slots_menu(callback: CallbackQuery):
    text = (
        "🎰 <b>Игровой Автомат</b>\n\n"
        "Три одинаковых символа = выигрыш!\n\n"
        "<b>Выплаты (множитель к ставке):</b>\n"
        "7️⃣ 7️⃣ 7️⃣ — x50\n"
        "💎 💎 💎 — x25\n"
        "⭐ ⭐ ⭐ — x15\n"
        "🔔 🔔 🔔 — x10\n"
        "🍋 🍋 🍋 — x5\n"
        "🍒 🍒 🍒 — x3\n"
        "Два одинаковых — x1 (возврат ставки)"
    )
    await callback.message.edit_text(text, reply_markup=get_slots_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("slots_spin_"))
async def cb_slots_spin(callback: CallbackQuery, db: Database):
    bet = int(callback.data.split("_")[2])

    if not await db.deduct_coins(callback.from_user.id, bet):
        return await callback.answer(f"Недостаточно коинов! Нужно {bet} 🪙", show_alert=True)

    r1 = random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]
    r2 = random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]
    r3 = random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]

    await callback.message.edit_text(f"🎰 <b>Крутим...</b>\n\n| ❓ | ❓ | ❓ |")
    await asyncio.sleep(1)

    result = (r1, r2, r3)
    multiplier = PAYOUTS.get(result, 0)

    if multiplier == 0 and (r1 == r2 or r2 == r3 or r1 == r3):
        multiplier = 1

    winnings = bet * multiplier
    if winnings > 0:
        await db.add_coins(callback.from_user.id, winnings)

    line = f"| {r1} | {r2} | {r3} |"

    if multiplier >= 10:
        text = f"🎰 <b>ДЖЕКПОТ!</b>\n\n{line}\n\n🎉 Выигрыш: <b>{winnings} 🪙</b> (x{multiplier})!"
    elif multiplier > 1:
        text = f"🎰 <b>Есть совпадение!</b>\n\n{line}\n\n✨ Выигрыш: <b>{winnings} 🪙</b> (x{multiplier})"
    elif multiplier == 1:
        text = f"🎰 <b>Почти!</b>\n\n{line}\n\n🔄 Ставка возвращена: {winnings} 🪙"
    else:
        text = f"🎰 <b>Мимо...</b>\n\n{line}\n\n💸 Вы потеряли {bet} 🪙"

    await callback.message.edit_text(text, reply_markup=get_slots_kb())
    await callback.answer()
