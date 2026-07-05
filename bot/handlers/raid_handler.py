from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.repository import Database
from aiogram.fsm.context import FSMContext
import time
import random

router = Router()

def get_raid_kb(boss_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"raid_attack_{boss_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_raid")
async def cb_eco_raid(callback: CallbackQuery, db: Database):
    # Fetch active raid
    async with db._conn.execute('SELECT id, boss_name, hp, max_hp, end_time FROM active_raids WHERE hp > 0 ORDER BY id DESC LIMIT 1') as cursor:
        boss = await cursor.fetchone()
        
    if not boss:
        # Check if we already spawned a boss recently
        async with db._conn.execute('SELECT id FROM active_raids WHERE end_time > ? ORDER BY id DESC LIMIT 1', (time.time() - 86400,)) as cursor:
            recent_boss = await cursor.fetchone()
            
        if recent_boss:
            await callback.message.edit_text("⏳ Босс повержен! Новый босс появится позже.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]]))
            return
            
        # Spawn a new boss if none exists and no recent boss!
        bosses = [("Злой Учитель Математики", 10000), ("Хулиган из старших классов", 15000), ("Гигантский Слизь", 25000)]
        name, max_hp = random.choice(bosses)
        end_time = time.time() + 86400 # 24 hours
        
        cursor = await db._conn.execute('INSERT INTO active_raids (boss_name, hp, max_hp, end_time) VALUES (?, ?, ?, ?)', (name, max_hp, max_hp, end_time))
        boss_id = cursor.lastrowid
        await db._conn.commit()
        boss = (boss_id, name, max_hp, max_hp, end_time)
        
    boss_id, name, hp, max_hp, end_time = boss
    
    if time.time() > end_time:
        await db._conn.execute('UPDATE active_raids SET hp = 0 WHERE id = ?', (boss_id,))
        await db._conn.commit()
        await callback.message.edit_text("⏳ Время рейда истекло! Босс сбежал.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]]))
        return
        
    from utils.formatting import generate_progress_bar
    bar = generate_progress_bar(hp, max_hp, length=15)
    
    text = (f"👹 <b>ГЛОБАЛЬНЫЙ БОСС</b> 👹\n\n"
            f"<b>Имя:</b> {name}\n"
            f"<b>HP:</b> {hp}/{max_hp}\n"
            f"└ {bar}\n\n"
            f"<i>Атакуйте босса вместе с другими игроками! За добивание и участие вы получите огромную награду!</i>")
            
    await callback.message.edit_text(text, reply_markup=get_raid_kb(boss_id), parse_mode="HTML")
    
raid_cooldowns = {}

@router.callback_query(F.data.startswith("raid_attack_"))
async def cb_raid_attack(callback: CallbackQuery, db: Database):
    boss_id = int(callback.data.split("_")[-1])
    
    # In-memory cooldown check to prevent race conditions
    user_id = callback.from_user.id
    now = time.time()
    if user_id in raid_cooldowns and now - raid_cooldowns[user_id] < 10:
        await callback.answer("⏳ Вы восстанавливаете выносливость! Ждите 10 секунд.", show_alert=True)
        return
    raid_cooldowns[user_id] = now
    
    # Check cooldown in db just in case

    # (Using transactions table as a quick cooldown tracker for raid)
    async with db._conn.execute('SELECT timestamp FROM transactions WHERE sender_id = ? AND action_type = ? ORDER BY timestamp DESC LIMIT 1', (callback.from_user.id, f"raid_attack_{boss_id}")) as cursor:
        last_attack = await cursor.fetchone()
        
    if last_attack and time.time() - last_attack[0] < 10:
        await callback.answer("⏳ Вы восстанавливаете выносливость! Ждите 10 секунд перед следующей атакой.", show_alert=True)
        return
        
    async with db._conn.execute('SELECT id, boss_name, hp, max_hp FROM active_raids WHERE id = ?', (boss_id,)) as cursor:
        boss = await cursor.fetchone()
        
    if not boss or boss[2] <= 0:
        await callback.answer("Этот босс уже повержен!", show_alert=True)
        return
        
    _, name, hp, max_hp = boss
    
    # Calculate Damage
    damage = random.randint(10, 50)
    
    # Check user cards for buffs
    cards = await db.get_user_cards(callback.from_user.id)
    if cards:
        # Sum stats from top 3 cards
        sorted_cards = sorted(cards, key=lambda x: x[5] * x[2], reverse=True)[:3]
        card_bonus = sum(c[5] * c[2] for c in sorted_cards)
        damage += card_bonus
        
    # Check pet buff
    pet = await db.get_user_pet(callback.from_user.id)
    if pet:
        _, _, _, _, p_hunger, p_happy, _ = pet
        if p_hunger > 50 and p_happy > 50:
            damage = int(damage * 1.5) # 50% damage boost if pet is happy
            
    new_hp = max(0, hp - damage)
    
    await db._conn.execute('UPDATE active_raids SET hp = ? WHERE id = ?', (new_hp, boss_id))
    await db.add_transaction(callback.from_user.id, boss_id, damage, f"raid_attack_{boss_id}")
    await db._conn.commit()
    
    if new_hp <= 0:
        # Boss dead, reward proportionally to all who attacked!
        async with db._conn.execute('SELECT sender_id, SUM(amount) FROM transactions WHERE action_type = ? GROUP BY sender_id', (f"raid_attack_{boss_id}",)) as cursor:
            attackers = await cursor.fetchall()
            
        reward_pool = 50000 # 50k total coins pool
        xp_pool = 10000
        
        for atk_id, total_dmg in attackers:
            dmg_percent = total_dmg / max_hp
            u_coins = int(reward_pool * dmg_percent)
            u_xp = int(xp_pool * dmg_percent)
            
            u = await db.get_user(atk_id)
            if u:
                u.coins += u_coins
                u.xp += u_xp
                await db.update_user(u)
                
        await callback.message.edit_text(f"🎉 <b>ПОБЕДА!</b> 🎉\n\nВы нанесли последний удар боссу <b>{name}</b>!\nНаграды были распределены между всеми участниками пропорционально их урону.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]]))
        await callback.answer()
    else:
        # Mini reward for every hit
        user = await db.get_user(callback.from_user.id)
        user.coins += 10
        await db.update_user(user)
        
        await callback.answer(f"💥 Вы нанесли {damage} урона боссу! (+10 🪙)", show_alert=True)
        await cb_eco_raid(callback, db) # Refresh UI
