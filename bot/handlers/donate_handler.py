from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.text_decorations import html_decoration
from database.repository import Database
from config.settings import get_settings
from bot.fsm.states import DonateStates

router = Router()
settings = get_settings()

# Custom-amount donations: how many coins per star, and the allowed star range.
COINS_PER_STAR = 15
MIN_STARS = 1
MAX_STARS = 10000

def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_USER_IDS

def get_donate_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🪙 500 MahiroCoins (⭐️ 50)", callback_data="buy_stars_50")],
        [InlineKeyboardButton(text="🪙 1500 MahiroCoins (⭐️ 100)", callback_data="buy_stars_100")],
        [InlineKeyboardButton(text="💎 VIP-статус + 5000 🪙 (⭐️ 500)", callback_data="buy_stars_500")],
        [InlineKeyboardButton(text="✍️ Своя сумма (⭐️)", callback_data="buy_custom")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(F.text.in_(["/donate", "💝 Поддержать проект"]))
async def cmd_donate(message: Message):
    text = ("💝 <b>Поддержать разработку и развитие Махиро</b> 💝\n\n"
            "Спасибо, что играете и общаетесь со мной! Содержание серверов и новые функции требуют ресурсов.\n\n"
            "Вы можете безопасно и быстро поддержать проект через <b>Telegram Stars (⭐️)</b>, купив игровые монеты или VIP-статус!")
    await message.answer(text, reply_markup=get_donate_kb())

@router.callback_query(F.data.startswith("buy_stars_"))
async def process_buy_stars(callback: CallbackQuery, bot: Bot):
    amount_stars = int(callback.data.split("_")[2])
    
    if amount_stars == 50:
        title = "500 MahiroCoins"
        description = "Пакет из 500 монет для покупки подарков и использования в экономике бота."
        payload = "buy_coins_500"
    elif amount_stars == 100:
        title = "1500 MahiroCoins"
        description = "Большой пакет монет. Хватит надолго!"
        payload = "buy_coins_1500"
    elif amount_stars == 500:
        title = "VIP-статус + 5000 Монет"
        description = "Огромная поддержка! Получи VIP и кучу монет!"
        payload = "buy_vip"
    else:
        return
        
    prices = [LabeledPrice(label=title, amount=amount_stars)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="", # Empty for Telegram Stars
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@router.callback_query(F.data == "buy_custom")
async def cb_buy_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DonateStates.waiting_for_custom_amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="donate_cancel")]])
    await callback.message.answer(
        f"✍️ Введите количество звёзд ⭐️ (от {MIN_STARS} до {MAX_STARS}).\n\n"
        f"За каждую ⭐️ вы получите <b>{COINS_PER_STAR} 🪙</b>.",
        reply_markup=kb,
    )
    await callback.answer()

@router.callback_query(F.data == "donate_cancel")
async def cb_donate_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Ок, отменили. Загляни в /donate, когда захочешь поддержать проект. 🌸")
    await callback.answer()

@router.message(DonateStates.waiting_for_custom_amount)
async def process_custom_amount(message: Message, state: FSMContext, bot: Bot):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(f"Нужно число от {MIN_STARS} до {MAX_STARS}. Попробуй ещё раз или нажми Отмена.")
        return
    stars = int(text)
    if stars < MIN_STARS or stars > MAX_STARS:
        await message.answer(f"Сумма должна быть от {MIN_STARS} до {MAX_STARS} ⭐️. Попробуй ещё раз.")
        return

    await state.clear()
    coins = stars * COINS_PER_STAR
    title = f"{coins} MahiroCoins"
    prices = [LabeledPrice(label=title, amount=stars)]
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title=title,
        description=f"Пакет из {coins} монет за {stars} ⭐️ Telegram Stars.",
        payload=f"buy_custom_{stars}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Always answer True to proceed
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, db: Database):
    payload = message.successful_payment.invoice_payload
    user = await db.get_user(message.from_user.id)

    coins_granted = 0
    reply = None

    if payload == 'buy_coins_500':
        coins_granted = 500
        user.coins += 500
        reply = "🎉 Спасибо за поддержку! Тебе начислено <b>500 🪙 MahiroCoins</b>!"
    elif payload == 'buy_coins_1500':
        coins_granted = 1500
        user.coins += 1500
        reply = "🎉 Ого! Спасибо огромное! Тебе начислено <b>1500 🪙 MahiroCoins</b>!"
    elif payload == 'buy_vip':
        coins_granted = 5000
        user.coins += 5000
        user.is_vip = True
        user.xp += 1000
        reply = "🎉 ТЫ ЛУЧШИЙ! Спасибо за невероятную поддержку! Тебе начислен <b>VIP-статус</b> (теперь он будет отображаться в твоем профиле) и <b>5000 🪙 MahiroCoins</b>!"
    elif payload.startswith('buy_custom_'):
        coins_granted = int(payload.split('_')[2]) * COINS_PER_STAR
        user.coins += coins_granted
        reply = f"🎉 Спасибо за поддержку! Тебе начислено <b>{coins_granted} 🪙 MahiroCoins</b>!"
    else:
        return

    # Persist the grant and record the transaction BEFORE replying, so a failure
    # here never leaves the user thanked but uncredited / unaudited.
    await db.update_user(user)
    await db.add_transaction(0, user.id, coins_granted, "stars_purchase")

    # Store the payment (with charge_id) so an admin can refund it later.
    sp = message.successful_payment
    granted_vip = payload == "buy_vip"
    payment_id = await db.add_star_payment(
        user.id, sp.telegram_payment_charge_id, sp.total_amount, coins_granted, granted_vip
    )

    await message.answer(reply)

    # Notify admins with a one-tap refund button (payment_id keeps callback_data short).
    uname = html_decoration.quote(message.from_user.username or "без юзернейма")
    notify = (f"⭐️ <b>Новый донат</b>\n\nОт: {message.from_user.id} (@{uname})\n"
              f"Сумма: {sp.total_amount} ⭐️ → {coins_granted} 🪙" + (" + VIP" if granted_vip else ""))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Вернуть Stars", callback_data=f"refund_ask:{payment_id}")]
    ])
    for admin_id in settings.ADMIN_USER_IDS:
        try:
            await message.bot.send_message(admin_id, notify, reply_markup=kb)
        except Exception:
            pass


async def _do_refund(bot: Bot, db: Database, payment_id: int) -> str:
    """Refund a Stars payment and claw back the granted coins/VIP. Returns a status string."""
    payment = await db.get_star_payment(payment_id)
    if not payment:
        return "❌ Платёж не найден."
    _pid, uid, charge_id, stars, coins, vip, refunded = payment
    if refunded:
        return "⚠️ Этот платёж уже возвращён."

    # Reserve atomically so a double click can't refund twice.
    if not await db.mark_star_payment_refunded(payment_id):
        return "⚠️ Этот платёж уже возвращён."

    try:
        await bot.refund_star_payment(user_id=uid, telegram_payment_charge_id=charge_id)
    except Exception as e:
        # Roll back the reservation so it can be retried.
        await db._conn.execute('UPDATE star_payments SET refunded = 0 WHERE id = ?', (payment_id,))
        await db._conn.commit()
        return f"❌ Ошибка возврата: {e}"

    # Claw back what was granted (clamped so the balance never goes negative).
    user = await db.get_user(uid)
    user.coins = max(0, user.coins - coins)
    if vip:
        user.is_vip = False
    await db.update_user(user)
    await db.add_transaction(uid, 0, coins, "stars_refund")

    try:
        await bot.send_message(uid, f"↩️ Ваш донат на {stars} ⭐️ возвращён. Начисленные {coins} 🪙"
                                    + (" и VIP" if vip else "") + " списаны.")
    except Exception:
        pass
    return f"✅ Возврат выполнен: {stars} ⭐️ пользователю {uid}. Списано {coins} 🪙" + (" и VIP." if vip else ".")


@router.callback_query(F.data.startswith("refund_ask:"))
async def cb_refund_ask(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    payment_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, вернуть", callback_data=f"refund_do:{payment_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="refund_cancel")]
    ])
    await callback.message.answer("Точно вернуть этот платёж? Начисленные коины (и VIP) будут списаны.", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("refund_do:"))
async def cb_refund_do(callback: CallbackQuery, db: Database):
    if not _is_admin(callback.from_user.id):
        return
    payment_id = int(callback.data.split(":")[1])
    result = await _do_refund(callback.bot, db, payment_id)
    await callback.message.edit_text(result)
    await callback.answer()


@router.callback_query(F.data == "refund_cancel")
async def cb_refund_cancel(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("Возврат отменён.")
    await callback.answer()


@router.message(F.text.startswith("/refund "))
async def cmd_refund(message: Message, db: Database):
    if not _is_admin(message.from_user.id):
        return
    charge_id = message.text.split(maxsplit=1)[1].strip()
    payment = await db.get_star_payment_by_charge(charge_id)
    if not payment:
        await message.answer("❌ Платёж с таким charge_id не найден.")
        return
    result = await _do_refund(message.bot, db, payment[0])
    await message.answer(result)
