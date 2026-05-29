from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.repository import Database
from bot.fsm.states import ClanStates

router = Router()

def get_clan_menu_kb(has_clan: bool) -> InlineKeyboardMarkup:
    kb = []
    if not has_clan:
        kb.append([InlineKeyboardButton(text="⚔️ Создать Клан (10,000 🪙)", callback_data="clan_create")])
        kb.append([InlineKeyboardButton(text="🏆 Топ Кланов", callback_data="clan_top")])
    else:
        kb.append([InlineKeyboardButton(text="👤 Мой Клан", callback_data="clan_my")])
        kb.append([InlineKeyboardButton(text="💰 Пожертвовать в Казну", callback_data="clan_donate")])
        kb.append([InlineKeyboardButton(text="🏆 Топ Кланов", callback_data="clan_top")])
        kb.append([InlineKeyboardButton(text="🚪 Покинуть Клан", callback_data="clan_leave")])
    
    kb.append([InlineKeyboardButton(text="⬅️ Назад в Меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_clans")
async def cb_clans_main(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    text = "🏰 **Система Кланов**\n\nОбъединяйтесь с другими игроками, пополняйте казну и соревнуйтесь в Топе!"
    await callback.message.edit_text(text, reply_markup=get_clan_menu_kb(bool(user_clan)))

@router.callback_query(F.data == "clan_create")
async def cb_clan_create(callback: CallbackQuery, db: Database, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if user.coins < 10000:
        await callback.answer("Недостаточно коинов! Нужно 10,000 🪙", show_alert=True)
        return
    await state.set_state(ClanStates.waiting_for_clan_name)
    await callback.message.answer("Введите название для вашего нового клана (до 20 символов):")
    await callback.answer()

@router.message(ClanStates.waiting_for_clan_name)
async def process_clan_name(message: Message, state: FSMContext, db: Database):
    name = message.text.strip()
    if len(name) > 20:
        await message.answer("Слишком длинное название. Попробуйте еще раз:")
        return
    
    existing = await db.get_clan_by_name(name)
    if existing:
        await message.answer("Клан с таким названием уже существует! Придумайте другое:")
        return
        
    user = await db.get_user(message.from_user.id)
    if user.coins < 10000:
        await message.answer("Не хватает коинов.")
        await state.clear()
        return
        
    user.coins -= 10000
    await db.update_user(user)
    
    clan_id = await db.create_clan(name, user.id)
    await db.add_transaction(user.id, 0, 10000, "clan_create")
    
    await message.answer(f"🎉 Клан **{name}** успешно создан!")
    await state.clear()

@router.callback_query(F.data == "clan_my")
async def cb_clan_my(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan:
        await callback.answer("У вас нет клана!", show_alert=True)
        return
        
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    members = await db.get_clan_members(c_id)
    
    text = f"🏰 **Клан: {c_name}**\n"
    text += f"📊 Уровень: {c_level} (Опыт: {c_xp})\n"
    text += f"💰 Казна: {c_treasury} 🪙\n"
    text += f"👥 Участников: {len(members)}\n\n"
    text += f"Ваша роль: {role}"
    
    await callback.message.edit_text(text, reply_markup=get_clan_menu_kb(True))

@router.callback_query(F.data == "clan_top")
async def cb_clan_top(callback: CallbackQuery, db: Database):
    async with db._conn.execute('SELECT name, level, xp, treasury FROM clans ORDER BY xp DESC LIMIT 10') as cursor:
        rows = await cursor.fetchall()
    
    if not rows:
        await callback.answer("Еще нет созданных кланов.", show_alert=True)
        return
        
    text = "🏆 **Топ 10 Кланов сервера**\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. **{row[0]}** - Ур. {row[1]} (Опыт: {row[2]}) | 🪙 {row[3]}\n"
        
    user_clan = await db.get_user_clan(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=get_clan_menu_kb(bool(user_clan)))

@router.callback_query(F.data == "clan_donate")
async def cb_clan_donate(callback: CallbackQuery, state: FSMContext, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan:
        await callback.answer("У вас нет клана!", show_alert=True)
        return
        
    await state.set_state(ClanStates.waiting_for_donate)
    await callback.message.answer("Сколько 🪙 вы хотите пожертвовать в казну клана?")
    await callback.answer()

@router.message(ClanStates.waiting_for_donate)
async def process_clan_donate(message: Message, state: FSMContext, db: Database):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return
        
    user = await db.get_user(message.from_user.id)
    if user.coins < amount:
        await message.answer(f"Недостаточно коинов. Ваш баланс: {user.coins} 🪙")
        await state.clear()
        return
        
    user_clan = await db.get_user_clan(user.id)
    if not user_clan:
        await message.answer("Вы уже не состоите в клане.")
        await state.clear()
        return
        
    c_id = user_clan[0]
    user.coins -= amount
    await db.update_user(user)
    await db.update_clan_treasury(c_id, amount)
    # Give some XP to the clan
    await db._conn.execute('UPDATE clans SET xp = xp + ? WHERE id = ?', (amount // 10, c_id))
    await db._conn.commit()
    
    await message.answer(f"✅ Вы пожертвовали {amount} 🪙 в казну клана! Клан получил {amount // 10} XP.")
    await state.clear()

@router.callback_query(F.data == "clan_leave")
async def cb_clan_leave(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan:
        await callback.answer("У вас нет клана!", show_alert=True)
        return
        
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    
    if role == 'owner':
        await callback.answer("Владелец не может просто так покинуть клан. (Функция роспуска в разработке)", show_alert=True)
        return
        
    await db.remove_clan_member(c_id, callback.from_user.id)
    await callback.answer("Вы успешно покинули клан.", show_alert=True)
    await callback.message.edit_text("Вы покинули клан.", reply_markup=get_clan_menu_kb(False))
