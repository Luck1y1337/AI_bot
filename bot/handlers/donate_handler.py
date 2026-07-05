from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
from config.settings import get_settings

router = Router()
settings = get_settings()

def get_donate_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🪙 500 MahiroCoins (⭐️ 50)", callback_data="buy_stars_50")],
        [InlineKeyboardButton(text="🪙 1500 MahiroCoins (⭐️ 100)", callback_data="buy_stars_100")],
        [InlineKeyboardButton(text="💎 VIP-статус + 5000 🪙 (⭐️ 500)", callback_data="buy_stars_500")]
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
    else:
        return

    # Persist the grant and record the transaction BEFORE replying, so a failure
    # here never leaves the user thanked but uncredited / unaudited.
    await db.update_user(user)
    await db.add_transaction(0, user.id, coins_granted, "stars_purchase")
    await message.answer(reply)
