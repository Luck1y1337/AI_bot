from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database

router = Router()

TICKET_PRICE = 100
MAX_TICKETS_PER_USER = 10


def get_lottery_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=f"🎟 Купить билет ({TICKET_PRICE} 🪙)", callback_data="lottery_buy")],
        [InlineKeyboardButton(text="🎟 x5 билетов", callback_data="lottery_buy_5")],
        [InlineKeyboardButton(text="🔙 Назад в Игры", callback_data="cat_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.callback_query(F.data == "eco_lottery")
async def cb_lottery_menu(callback: CallbackQuery, db: Database):
    round_id = await db.get_current_lottery_round()
    total_tickets, total_players = await db.get_lottery_pool(round_id)
    user_tickets = await db.get_user_tickets(callback.from_user.id, round_id)
    jackpot = total_tickets * TICKET_PRICE

    text = (
        "🎟 <b>Еженедельная Лотерея</b>\n\n"
        f"💰 Текущий джекпот: <b>{jackpot} 🪙</b>\n"
        f"🎟 Продано билетов: {total_tickets}\n"
        f"👥 Участников: {total_players}\n\n"
        f"Ваших билетов: <b>{user_tickets}</b> / {MAX_TICKETS_PER_USER}\n"
        f"Цена билета: {TICKET_PRICE} 🪙\n\n"
        "Розыгрыш происходит автоматически раз в неделю.\n"
        "Чем больше билетов — тем выше шанс!"
    )
    await callback.message.edit_text(text, reply_markup=get_lottery_kb())
    await callback.answer()


async def _buy_tickets(callback: CallbackQuery, db: Database, count: int):
    round_id = await db.get_current_lottery_round()
    user_tickets = await db.get_user_tickets(callback.from_user.id, round_id)

    if user_tickets + count > MAX_TICKETS_PER_USER:
        remaining = MAX_TICKETS_PER_USER - user_tickets
        return await callback.answer(
            f"Максимум {MAX_TICKETS_PER_USER} билетов! Можно купить ещё {remaining}.",
            show_alert=True
        )

    total_cost = TICKET_PRICE * count
    if not await db.deduct_coins(callback.from_user.id, total_cost):
        return await callback.answer(f"Недостаточно коинов! Нужно {total_cost} 🪙", show_alert=True)

    for _ in range(count):
        await db.buy_lottery_ticket(callback.from_user.id, round_id)

    await callback.answer(f"Куплено {count} билет(ов)!", show_alert=True)
    await cb_lottery_menu(callback, db)


@router.callback_query(F.data == "lottery_buy")
async def cb_lottery_buy(callback: CallbackQuery, db: Database):
    await _buy_tickets(callback, db, 1)


@router.callback_query(F.data == "lottery_buy_5")
async def cb_lottery_buy_5(callback: CallbackQuery, db: Database):
    await _buy_tickets(callback, db, 5)
