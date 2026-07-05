from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database

router = Router()

def get_customization_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔲 Рамка: Обычная (0 🪙)", callback_data="buy_frame_default")],
        [InlineKeyboardButton(text="🌟 Рамка: Золотая (5,000 🪙)", callback_data="buy_frame_gold")],
        [InlineKeyboardButton(text="🟢 Рамка: Неоновая (10,000 🪙)", callback_data="buy_frame_neon")],
        [InlineKeyboardButton(text="🩸 Рамка: Кровавая (20,000 🪙)", callback_data="buy_frame_blood")],
        [InlineKeyboardButton(text="💎 Рамка: Алмазная (50,000 🪙)", callback_data="buy_frame_diamond")],
        [InlineKeyboardButton(text="🔙 Назад в Магазин", callback_data="eco_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_customization")
async def cb_customization(callback: CallbackQuery):
    text = "🎨 <b>Магазин Кастомизации</b>\n\nЗдесь вы можете изменить рамку вокруг вашей аватарки в команде /stats! После покупки рамка применится автоматически."
    await callback.message.edit_text(text, reply_markup=get_customization_kb())

@router.callback_query(F.data.startswith("buy_frame_"))
async def cb_buy_frame(callback: CallbackQuery, db: Database):
    frame = callback.data.replace("buy_frame_", "")
    user_id = callback.from_user.id
    
    prices = {
        "default": 0,
        "gold": 5000,
        "neon": 10000,
        "blood": 20000,
        "diamond": 50000
    }
    price = prices.get(frame, 0)
    
    if price > 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить покупку", callback_data=f"confirm_frame_{frame}"),
             InlineKeyboardButton(text="❌ Отмена", callback_data="eco_customization")]
        ])
        await callback.message.edit_text(f"Вы уверены, что хотите купить эту рамку за {price} 🪙?", reply_markup=kb)
    else:
        await db.update_profile_frame(user_id, frame)
        await callback.answer("Рамка успешно установлена!", show_alert=True)

@router.callback_query(F.data.startswith("confirm_frame_"))
async def cb_confirm_frame(callback: CallbackQuery, db: Database):
    frame = callback.data.replace("confirm_frame_", "")
    user_id = callback.from_user.id
    
    prices = {"default": 0, "gold": 5000, "neon": 10000, "blood": 20000, "diamond": 50000}
    price = prices.get(frame, 0)
    
    if price > 0:
        if not await db.deduct_coins(user_id, price):
            return await callback.answer("У вас недостаточно коинов!", show_alert=True)
            
    await db.update_profile_frame(user_id, frame)
    await callback.message.edit_text("✅ Рамка успешно куплена и установлена!", reply_markup=get_customization_kb())
    await callback.answer()
