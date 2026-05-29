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
        # Spawn a new boss if none exists!
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
        
    hp_bar_len = 20
    fill = int((hp / max_hp) * hp_bar_len)
    bar = "🟩" * fill + "⬛" * (hp_bar_len - fill)
    
    text = (f"👹 **ГЛОБАЛЬНЫЙ БОСС** 👹\n\n"
            f"Имя: {name}\n"
            f"HP: {hp}/{max_hp}\n"
            f"[{bar}]\n\n"
            f"Атакуйте босса вместе с другими игроками! За добивание и участие вы получите огромную награду!")
            
    await callback.message.edit_text(text, reply_markup=get_raid_kb(boss_id))
    
@router.callback_query(F.data.startswith("raid_attack_"))
async def cb_raid_attack(callback: CallbackQuery, db: Database):
    boss_id = int(callback.data.split("_")[-1])
    
    # Check cooldown
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
        # Boss dead, reward!
        user = await db.get_user(callback.from_user.id)
        user.coins += 5000
        user.xp += 1000
        await db.update_user(user)
        
        await callback.message.edit_text(f"🎉 **ПОБЕДА!** 🎉\n\nВы нанесли последний удар ({damage} урона) и повергли босса **{name}**!\n\nВы получаете:\n💰 5000 🪙\n✨ 1000 XP", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="menu_games")]]))
        await callback.answer()
    else:
        await callback.answer(f"💥 Вы нанесли {damage} урона боссу!", show_alert=True)
        await cb_eco_raid(callback, db) # Refresh UI
