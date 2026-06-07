from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
from bot.fsm.states import MarryStates
from aiogram.fsm.context import FSMContext
from bot.keyboards.main_kb import get_social_users_kb, get_eco_social_kb

router = Router()

def get_house_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🪑 Купить мебель (1000 🪙)", callback_data="house_buy_furniture")],
        [InlineKeyboardButton(text="💔 Развод", callback_data="house_divorce")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cat_social")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_marry")
async def cb_eco_marry(callback: CallbackQuery, db: Database, state: FSMContext):
    marriage = await db.get_marriage(callback.from_user.id)
    if marriage:
        u1, u2 = marriage[0], marriage[1]
        partner_id = u2 if u1 == callback.from_user.id else u1
        
        # House Logic
        house = await db.get_marriage_house(u1, u2)
        if not house:
            await db.create_marriage_house(u1, u2)
            house = (1, 0) # level 1, 0 fp
            
        level, fp = house
        bonus = level * 10
        
        text = f"💍 **Ваш Брак с {partner_id}**\n\n"
        text += f"🏡 **Совместный Дом (Ур. {level})**\n"
        text += f"Очки уюта (Мебель): {fp} / {level * 5}\n"
        text += f"Текущий пассивный бонус обоим: **+{bonus}%** к доходу бизнесов!\n\n"
        text += "Покупайте мебель, чтобы повышать уют. Когда шкала уюта заполнится, дом повысит уровень!"
        
        await callback.message.edit_text(text, reply_markup=get_house_kb())
        return
        
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    if not users:
        await callback.answer("Нет доступных партнеров.", show_alert=True)
        return
    await state.set_state(MarryStates.waiting_for_partner)
    await callback.message.edit_text("💍 **Предложение руки и сердца**\n\nВыберите партнера:", reply_markup=get_social_users_kb(users, 0))

@router.callback_query(F.data == "house_buy_furniture")
async def cb_house_buy_furniture(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    marriage = await db.get_marriage(user_id)
    if not marriage: return await callback.answer("Вы не в браке!", show_alert=True)
    
    if not await db.deduct_coins(user_id, 1000):
        return await callback.answer("Не хватает 1000 🪙!", show_alert=True)
        
    u1, u2 = marriage[0], marriage[1]
    house = await db.get_marriage_house(u1, u2)
    level, fp = house
    
    fp += 1
    if fp >= level * 5:
        level += 1
        fp = 0
        await callback.answer("Ура! Ваш дом повышен в уровне!", show_alert=True)
    else:
        await callback.answer("Вы купили новую мебель! +1 Уют", show_alert=True)
        
    await db.update_marriage_house(u1, u2, level, fp)
    await db.add_transaction(user_id, 0, 1000, "buy_furniture")
    
    # Re-render
    await cb_eco_marry(callback, db, None)

@router.callback_query(F.data == "house_divorce")
async def cb_house_divorce(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    marriage = await db.get_marriage(user_id)
    if not marriage: return await callback.answer("Вы не в браке!", show_alert=True)
    
    u1, u2 = marriage[0], marriage[1]
    await db._conn.execute('DELETE FROM marriages WHERE user1_id = ? AND user2_id = ?', (u1, u2))
    await db._conn.execute('DELETE FROM houses WHERE marriage_id_1 = ? AND marriage_id_2 = ?', (u1, u2))
    await db._conn.commit()
    
    await callback.answer("Вы успешно развелись.", show_alert=True)
    await callback.message.edit_text("🤝 **Социальное**\n\nВзаимодействуй с другими игроками!", reply_markup=get_eco_social_kb())

@router.callback_query(MarryStates.waiting_for_partner, F.data.startswith("pay_page_"))
async def marry_paginate(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users()
    users = [u for u in users if u.id != callback.from_user.id]
    await callback.message.edit_reply_markup(reply_markup=get_social_users_kb(users, page))
    await callback.answer()

@router.callback_query(MarryStates.waiting_for_partner, F.data.startswith("pay_select_"))
async def marry_select(callback: CallbackQuery, db: Database, state: FSMContext, bot: Bot):
    target_id = int(callback.data.split("_")[2])
    
    target_marriage = await db.get_marriage(target_id)
    if target_marriage:
        await callback.answer("Этот пользователь уже состоит в браке! 💔", show_alert=True)
        return
        
    user = await db.get_user(callback.from_user.id)
    if user.coins < 5000:
        await callback.answer("Для предложения нужно 5000 🪙 на кольца!", show_alert=True)
        return
        
    await state.clear()
    await callback.message.edit_text(f"💍 Вы сделали предложение пользователю {target_id}! Ожидаем его ответа (5000 🪙 будут списаны при согласии).")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept_{user.id}")],
        [InlineKeyboardButton(text="💔 Отказать", callback_data=f"marry_decline_{user.id}")]
    ])
    try:
        await bot.send_message(target_id, f"💍 Пользователь {user.id} предлагает вам вступить в брак!\nБрак дает вам Совместный Дом с баффами.", reply_markup=kb)
    except:
        await callback.message.answer(f"Не удалось отправить сообщение пользователю {target_id}.")

@router.callback_query(F.data.startswith("marry_accept_"))
async def cb_marry_accept(callback: CallbackQuery, db: Database, bot: Bot):
    proposer_id = int(callback.data.split("_")[2])
    target_id = callback.from_user.id
    
    if await db.get_marriage(target_id) or await db.get_marriage(proposer_id):
        await callback.message.edit_text("Кто-то из вас уже состоит в браке!")
        return
        
    if not await db.deduct_coins(proposer_id, 5000):
        await callback.message.edit_text("У инициатора больше нет 5000 🪙 на кольца! Свадьба отменяется.")
        try: await bot.send_message(proposer_id, f"💔 {target_id} согласился на брак, но у вас не хватило коинов!")
        except: pass
        return
        
    await db.add_marriage(proposer_id, target_id)
    # create house immediately
    await db.create_marriage_house(proposer_id, target_id)
    
    await callback.message.edit_text(f"🎉 Вы успешно вступили в брак с {proposer_id}!")
    try:
        await bot.send_message(proposer_id, f"🎉 Пользователь {target_id} согласился на брак! -5000 🪙 за кольца. Поздравляем!")
    except: pass

@router.callback_query(F.data.startswith("marry_decline_"))
async def cb_marry_decline(callback: CallbackQuery, bot: Bot):
    proposer_id = int(callback.data.split("_")[2])
    await callback.message.edit_text("Вы отказались от предложения.")
    try:
        await bot.send_message(proposer_id, f"💔 Пользователь {callback.from_user.id} отказался от вашего предложения руки и сердца.")
    except: pass

@router.callback_query(MarryStates.waiting_for_partner, F.data == "pay_cancel")
async def marry_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🤝 **Социальное**\n\nВзаимодействуй с другими игроками!", reply_markup=get_eco_social_kb())
    await callback.answer()
