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
    text = ("💝 **Поддержать разработку и развитие Махиро** 💝\n\n"
            "Спасибо, что играете и общаетесь со мной! Содержание серверов и новые функции требуют ресурсов.\n\n"
            "Вы можете безопасно и быстро поддержать проект через **Telegram Stars (⭐️)**, купив игровые монеты или VIP-статус!")
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
    
    if payload == 'buy_coins_500':
        user.coins += 500
        await message.answer("🎉 Спасибо за поддержку! Тебе начислено **500 🪙 MahiroCoins**!")
    elif payload == 'buy_coins_1500':
        user.coins += 1500
        await message.answer("🎉 Ого! Спасибо огромное! Тебе начислено **1500 🪙 MahiroCoins**!")
    elif payload == 'buy_vip':
        user.coins += 5000
        # In a real app we would set user.is_vip = True, for now we just give coins and XP
        user.xp += 1000
        await message.answer("🎉 ТЫ ЛУЧШИЙ! Спасибо за невероятную поддержку! Тебе начислен **VIP-статус** (скоро будет отображаться в профиле) и **5000 🪙 MahiroCoins**!")
        
    await db.update_user(user)
