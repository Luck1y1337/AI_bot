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
        kb.append([InlineKeyboardButton(text="🚪 Вступить в Клан", callback_data="clan_join")])
    else:
        kb.append([InlineKeyboardButton(text="👤 Мой Клан", callback_data="clan_my")])
        kb.append([InlineKeyboardButton(text="👥 Участники", callback_data="clan_members")])
        kb.append([InlineKeyboardButton(text="💰 В Казну", callback_data="clan_donate"),
                   InlineKeyboardButton(text="🏗️ Улучшить Базу", callback_data="clan_upgrade")])
        kb.append([InlineKeyboardButton(text="⚔️ Клановые Войны", callback_data="clan_wars_menu"),
                   InlineKeyboardButton(text="🐉 Клановый Рейд", callback_data="clan_boss_menu")])
        kb.append([InlineKeyboardButton(text="🏆 Топ Кланов", callback_data="clan_top"),
                   InlineKeyboardButton(text="🚪 Покинуть", callback_data="clan_leave")])
    
    kb.append([InlineKeyboardButton(text="« Назад в Меню", callback_data="eco_clans")])
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
        
    await state.update_data(new_clan_name=name)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить (10,000 🪙)", callback_data="confirm_clan_create")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clan_create")]
    ])
    await message.answer(f"Создание клана **{name}** будет стоить 10,000 🪙. Вы уверены?", reply_markup=kb)

@router.callback_query(F.data == "confirm_clan_create")
async def cb_confirm_clan_create(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    name = data.get("new_clan_name")
    
    if not name:
        return await callback.answer("Ошибка данных. Попробуйте снова.", show_alert=True)
        
    if not await db.deduct_coins(callback.from_user.id, 10000):
        await callback.message.edit_text("Не хватает коинов.")
        await state.clear()
        return
    
    clan_id = await db.create_clan(name, callback.from_user.id)
    await db.add_transaction(callback.from_user.id, 0, 10000, "clan_create")
    
    await callback.message.edit_text(f"🎉 Клан **{name}** успешно создан!")
    await state.clear()
    
@router.callback_query(F.data == "cancel_clan_create")
async def cb_cancel_clan_create(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Создание клана отменено.")
    await state.clear()

@router.callback_query(F.data == "clan_my")
async def cb_clan_my(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan:
        await callback.answer("У вас нет клана!", show_alert=True)
        return
        
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    members = await db.get_clan_members(c_id)
    
    text = f"🏰 <b>Клан: {c_name}</b>\n"
    text += f"📊 <b>Уровень:</b> {c_level} (Опыт: {c_xp})\n"
    text += f"💰 <b>Казна:</b> {c_treasury} 🪙\n"
    text += f"👥 <b>Участников:</b> {len(members)}\n\n"
    text += f"<i>Ваша роль: {role}</i>"
    
    await callback.message.edit_text(text, reply_markup=get_clan_menu_kb(True), parse_mode="HTML")

@router.callback_query(F.data == "clan_top")
async def cb_clan_top(callback: CallbackQuery, db: Database):
    async with db._conn.execute('SELECT name, level, xp, treasury FROM clans ORDER BY xp DESC LIMIT 10') as cursor:
        rows = await cursor.fetchall()
    
    if not rows:
        await callback.answer("Еще нет созданных кланов.", show_alert=True)
        return
        
    text = "🏆 <b>Топ 10 Кланов сервера</b>\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. <b>{row[0]}</b> - Ур. {row[1]} (Опыт: {row[2]}) | 🪙 {row[3]}\n"
        
    user_clan = await db.get_user_clan(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=get_clan_menu_kb(bool(user_clan)), parse_mode="HTML")

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
        
    user_clan = await db.get_user_clan(message.from_user.id)
    if not user_clan:
        await message.answer("Вы уже не состоите в клане.")
        await state.clear()
        return
        
    success = await db.deduct_coins(message.from_user.id, amount)
    if not success:
        await message.answer(f"Недостаточно коинов.")
        await state.clear()
        return
        
    c_id = user_clan[0]
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
        await db.delete_clan(c_id)
        await callback.answer(f"Вы распустили клан {c_name}.", show_alert=True)
        await callback.message.edit_text("Вы распустили клан.", reply_markup=get_clan_menu_kb(False))
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
    import random, time
    
    # Check cooldown using transactions
    async with db._conn.execute('SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = ? ORDER BY timestamp DESC LIMIT 1', (callback.from_user.id, 'clan_attack')) as cursor:
        last_attack = await cursor.fetchone()
        
    if last_attack and time.time() - last_attack[0] < 3600:
        mins_left = int((3600 - (time.time() - last_attack[0])) / 60)
        await callback.answer(f"⏳ Ваша армия отдыхает! Ждите {mins_left} мин.", show_alert=True)
        return
        
    await db.add_transaction(callback.from_user.id, 0, 0, 'clan_attack')
    
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

@router.callback_query(F.data == "clan_join")
async def cb_clan_join(callback: CallbackQuery, state: FSMContext, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if user_clan:
        await callback.answer("Вы уже состоите в клане!", show_alert=True)
        return
    await state.set_state(ClanStates.waiting_for_join_name)
    await callback.message.answer("Введите точное название клана, в который хотите вступить:", parse_mode="HTML")
    await callback.answer()

@router.message(ClanStates.waiting_for_join_name)
async def process_clan_join(message: Message, state: FSMContext, db: Database):
    name = message.text.strip()
    clan = await db.get_clan_by_name(name)
    if not clan:
        await message.answer("Клан с таким названием не найден. Попробуйте еще раз или напишите /cancel.")
        return
        
    c_id = clan[0]
    members = await db.get_clan_members(c_id)
    
    # Check limit (e.g., 20 max members per clan base level)
    async with db._conn.execute('SELECT base_level FROM clans WHERE id = ?', (c_id,)) as cursor:
        row = await cursor.fetchone()
        b_lvl = row[0] if row else 1
    max_members = 10 + (b_lvl * 5)
    
    if len(members) >= max_members:
        await message.answer(f"В клане <b>{name}</b> нет мест! Максимум {max_members} участников.", parse_mode="HTML")
        await state.clear()
        return
        
    await db.add_clan_member(c_id, message.from_user.id, role='member')
    await message.answer(f"🎉 Вы успешно вступили в клан <b>{name}</b>!", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "clan_members")
async def cb_clan_members(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return
    
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    members = await db.get_clan_members(c_id)
    
    text = f"👥 <b>Участники клана {c_name}</b>\n\n"
    for m_id, m_role, joined_at in members:
        import time
        days = int((time.time() - joined_at) / 86400)
        role_emoji = "👑" if m_role == 'owner' else "👤"
        text += f"{role_emoji} ID: <code>{m_id}</code> | В клане: {days} дн.\n"
        
    kb = []
    if role == 'owner':
        kb.append([InlineKeyboardButton(text="🚷 Выгнать участника", callback_data="clan_kick_menu")])
    kb.append([InlineKeyboardButton(text="« Назад", callback_data="clan_my")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data == "clan_kick_menu")
async def cb_clan_kick_menu(callback: CallbackQuery, state: FSMContext, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan or user_clan[6] != 'owner': return
    
    await state.set_state(ClanStates.waiting_for_kick_user)
    await callback.message.answer("Введите ID участника, которого хотите выгнать из клана:")
    await callback.answer()

@router.message(ClanStates.waiting_for_kick_user)
async def process_clan_kick(message: Message, state: FSMContext, db: Database):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Отмена.")
        await state.clear()
        return
        
    user_clan = await db.get_user_clan(message.from_user.id)
    if not user_clan or user_clan[6] != 'owner':
        await state.clear()
        return
        
    await db.remove_clan_member(c_id, target_id)
    await message.answer(f"✅ Участник {target_id} выгнан из клана.")
    try:
        await message.bot.send_message(target_id, f"Вы были исключены из клана <b>{user_clan[1]}</b>.", parse_mode="HTML")
    except: pass
    await state.clear()

# --- Clan Bosses ---
from utils.formatting import generate_progress_bar
import time

@router.callback_query(F.data == "clan_boss_menu")
async def cb_clan_boss_menu(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return await callback.answer("У вас нет клана!", show_alert=True)
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    
    boss = await db.get_clan_boss(c_id)
    kb = []
    if not boss:
        text = "🐉 <b>Клановый Рейд</b>\n\nСейчас нет активного босса."
        if role == 'owner':
            text += "\nВы можете призвать Древнего Дракона (стоимость: 5000 🪙 из казны)."
            kb.append([InlineKeyboardButton(text="🗡️ Призвать Дракона", callback_data="clan_boss_summon")])
    else:
        clan_id, boss_name, hp, max_hp, end_time = boss
        if time.time() > end_time or hp <= 0:
            if hp <= 0:
                text = f"🐉 <b>{boss_name} повержен!</b>\nПоздравляем! Ваш клан доказал свою мощь."
                # Reward distribution logic can be complex, for now just give XP and coins to clan
                if role == 'owner':
                    kb.append([InlineKeyboardButton(text="🎁 Забрать Награду (Лидер)", callback_data="clan_boss_claim")])
            else:
                text = f"🐉 <b>{boss_name} улетел...</b>\nКлан не успел победить босса за 24 часа. Рейд провален."
                if role == 'owner':
                    kb.append([InlineKeyboardButton(text="🧹 Очистить", callback_data="clan_boss_clear")])
        else:
            bar = generate_progress_bar(hp, max_hp, 15)
            hours_left = int((end_time - time.time()) / 3600)
            text = f"🐉 <b>Рейд: {boss_name}</b>\n\n"
            text += f"❤️ HP: {hp} / {max_hp}\n"
            text += f"`{bar}`\n\n"
            text += f"⏳ Осталось времени: {hours_left} ч.\nКаждый участник может атаковать босса раз в час!"
            kb.append([InlineKeyboardButton(text="⚔️ Атаковать", callback_data="clan_boss_attack")])
            
    kb.append([InlineKeyboardButton(text="« Назад в Клан", callback_data="clan_my")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data == "clan_boss_summon")
async def cb_clan_boss_summon(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan or user_clan[6] != 'owner': return await callback.answer("Только лидер может призвать босса!", show_alert=True)
    c_id, c_name, c_owner, c_level, c_xp, c_treasury, role = user_clan
    
    boss = await db.get_clan_boss(c_id)
    if boss: return await callback.answer("У вас уже есть активный босс!", show_alert=True)
    
    if c_treasury < 5000:
        return await callback.answer("Недостаточно средств в казне! Нужно 5000 🪙.", show_alert=True)
        
    await db.update_clan_treasury(c_id, -5000)
    
    max_hp = 5000 * c_level # HP scales with clan level
    await db.create_clan_boss(c_id, "Древний Дракон", max_hp, 24)
    
    await callback.answer("Босс успешно призван!", show_alert=True)
    await cb_clan_boss_menu(callback, db)

@router.callback_query(F.data == "clan_boss_attack")
async def cb_clan_boss_attack(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan: return await callback.answer("Вы не в клане!", show_alert=True)
    c_id = user_clan[0]
    
    boss = await db.get_clan_boss(c_id)
    if not boss or boss[2] <= 0 or time.time() > boss[4]:
        return await callback.answer("Босс мертв или время вышло!", show_alert=True)
        
    # Check cooldown (1 hour per user)
    # Reusing transactions table as a cooldown lock
    async with db._conn.execute('SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = "clan_boss_attack" ORDER BY timestamp DESC LIMIT 1', (callback.from_user.id,)) as cursor:
        last_atk = await cursor.fetchone()
    
    if last_atk and time.time() - last_atk[0] < 3600:
        mins = int(60 - (time.time() - last_atk[0]) / 60)
        return await callback.answer(f"Вы уже атаковали босса недавно! Отдыхайте еще {mins} мин.", show_alert=True)
        
    import random
    user_cards = await db.get_user_cards(callback.from_user.id)
    power = sum([c[5] * c[2] for c in user_cards]) # Sum of (stats * level) of all cards
    if power == 0: power = 10 # Base power if no cards
    
    dmg = random.randint(int(power * 0.8), int(power * 1.2))
    new_hp = max(0, boss[2] - dmg)
    
    await db.update_clan_boss_hp(c_id, new_hp)
    await db.add_transaction(callback.from_user.id, c_id, dmg, "clan_boss_attack")
    
    from utils.quests import increment_quest_progress
    await increment_quest_progress(callback.from_user.id, "boss_damage", dmg, db)
    
    await callback.answer(f"Вы нанесли {dmg} урона боссу!", show_alert=True)
    await cb_clan_boss_menu(callback, db)

@router.callback_query(F.data.in_(["clan_boss_claim", "clan_boss_clear"]))
async def cb_clan_boss_end(callback: CallbackQuery, db: Database):
    user_clan = await db.get_user_clan(callback.from_user.id)
    if not user_clan or user_clan[6] != 'owner': return await callback.answer("Только лидер может сделать это!", show_alert=True)
    c_id = user_clan[0]
    
    boss = await db.get_clan_boss(c_id)
    if not boss: return await callback.answer("Босса нет.", show_alert=True)
    
    if callback.data == "clan_boss_claim":
        if boss[2] > 0: return await callback.answer("Босс еще жив!", show_alert=True)
        reward = boss[3] * 2 # Reward scales with max HP
        await db.update_clan_treasury(c_id, reward)
        await db._conn.execute('UPDATE clans SET xp = xp + ? WHERE id = ?', (reward // 10, c_id))
        await callback.answer(f"Клан получил {reward} 🪙 в казну и {reward // 10} XP!", show_alert=True)
        
    await db.delete_clan_boss(c_id)
    await cb_clan_boss_menu(callback, db)
