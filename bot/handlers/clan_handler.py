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
        kb.append([InlineKeyboardButton(text="💰 В Казну", callback_data="clan_donate"),
                   InlineKeyboardButton(text="🏗️ Улучшить Базу", callback_data="clan_upgrade")])
        kb.append([InlineKeyboardButton(text="⚔️ Клановые Войны", callback_data="clan_wars_menu")])
        kb.append([InlineKeyboardButton(text="🏆 Топ Кланов", callback_data="clan_top"),
                   InlineKeyboardButton(text="🚪 Покинуть", callback_data="clan_leave")])
    
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

@router.callback_query(F.data == "clan_upgrade")
async def cb_clan_upgrade(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return
    
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    
    # We use a new column 'base_level' we added earlier. Wait, get_user_clan returns 7 items...
    # Let's get the base_level manually to avoid rewriting the whole SQL for now.
    async with db._conn.execute('SELECT base_level FROM clans WHERE id = ?', (c_id,)) as cursor:
        row = await cursor.fetchone()
        base_level = row[0] if row else 1
        
    cost = base_level * 5000
    
    if role != 'owner' and role != 'deputy':
        await callback.answer("Только лидер или зам могут улучшать базу!", show_alert=True)
        return
        
    if c_treasury < cost:
        await callback.answer(f"Недостаточно средств в казне! Нужно {cost} 🪙 (сейчас {c_treasury})", show_alert=True)
        return
        
    await db._conn.execute('UPDATE clans SET treasury = treasury - ?, base_level = base_level + 1 WHERE id = ?', (cost, c_id))
    await db._conn.commit()
    
    await callback.answer(f"🎉 База клана улучшена до уровня {base_level + 1}!", show_alert=True)
    await cb_clan_my(callback, db)
    
@router.callback_query(F.data == "clan_wars_menu")
async def cb_clan_wars_menu(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return
    
    c_id, c_name, _, _, _, _, role = user_clan
    
    war = await db.get_active_clan_war(c_id)
    
    if not war:
        if role != 'owner':
            text = "🛡️ **Клановые Войны**\n\nВ данный момент ваш клан не участвует в войне. Лидер клана может объявить войну случайному противнику!"
            kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="eco_clans")]]
        else:
            text = "🛡️ **Клановые Войны**\n\nВаш клан не в состоянии войны. Объявить войну случайному клану (Подбор по уровню)?"
            kb = [
                [InlineKeyboardButton(text="⚔️ Искать Противника", callback_data="clan_war_search")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_clans")]
            ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
        
    w_id, c1_id, c2_id, s1, s2, e_time = war
    import time
    
    is_clan1 = (c_id == c1_id)
    my_score = s1 if is_clan1 else s2
    enemy_score = s2 if is_clan1 else s1
    
    # Get enemy name
    enemy_id = c2_id if is_clan1 else c1_id
    enemy_clan = await db.get_clan(enemy_id)
    enemy_name = enemy_clan[1] if enemy_clan else "Неизвестный Клан"
    
    hours_left = int((e_time - time.time()) / 3600)
    
    text = (f"⚔️ **Война Кланов!** ⚔️\n\n"
            f"**{c_name}** 🆚 **{enemy_name}**\n\n"
            f"Ваши очки: {my_score} 🛡️\n"
            f"Очки врага: {enemy_score} 🗡️\n\n"
            f"⏳ Осталось времени: ~{hours_left} ч.\n\n"
            f"Атакуйте вражеский клан, чтобы заработать очки!")
            
    kb = [
        [InlineKeyboardButton(text="🔥 Атаковать Врага!", callback_data=f"clan_war_attack_{w_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_clans")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "clan_war_search")
async def cb_clan_war_search(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return
    c_id, c_name, _, c_level, _, _, _ = user_clan
    
    # Find enemy around same level
    async with db._conn.execute('SELECT id FROM clans WHERE id != ? AND level >= ? AND level <= ?', (c_id, max(1, c_level-2), c_level+2)) as cursor:
        enemies = await cursor.fetchall()
        
    if not enemies:
        await callback.answer("Подходящий противник не найден! Попробуйте позже.", show_alert=True)
        return
        
    import random
    enemy_id = random.choice(enemies)[0]
    
    # Check if enemy already in war
    enemy_war = await db.get_active_clan_war(enemy_id)
    if enemy_war:
        await callback.answer("Противник уже занят другой войной, попробуйте еще раз.", show_alert=True)
        return
        
    await db.start_clan_war(c_id, enemy_id)
    await callback.answer("⚔️ Война объявлена!", show_alert=True)
    await cb_clan_wars_menu(callback, db)

@router.callback_query(F.data.startswith("clan_war_attack_"))
async def cb_clan_war_attack(callback: CallbackQuery, db: Database):
    war_id = int(callback.data.split("_")[-1])
    
    # Simple cooldown via memory or transaction (simulated with random chance for simplicity to avoid long locks)
    import random, time
    damage = random.randint(5, 15)
    
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return
    c_id = user_clan[0]
    
    war = await db.get_active_clan_war(c_id)
    if not war or war[0] != war_id:
        await callback.answer("Эта война уже закончилась!", show_alert=True)
        return
        
    is_clan1 = (war[1] == c_id)
    
    # Calculate bonus from base level
    async with db._conn.execute('SELECT base_level FROM clans WHERE id = ?', (c_id,)) as cursor:
        row = await cursor.fetchone()
        b_lvl = row[0] if row else 1
    damage += b_lvl * 2
    
    await db.update_clan_war_score(war_id, is_clan1, damage)
    
    # Also reward user
    user = await db.get_user(callback.from_user.id)
    user.coins += damage * 2
    await db.update_user(user)
    
    await callback.answer(f"💥 Вы нанесли {damage} урона вражескому клану и заработали {damage*2} 🪙!", show_alert=True)
    await cb_clan_wars_menu(callback, db)
