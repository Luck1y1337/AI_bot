from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import time

router = Router()

def get_dungeon_start_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🌲 Войти в Темный Лес", callback_data="dungeon_enter_forest")],
        [InlineKeyboardButton(text="🔙 Назад в Меню", callback_data="cat_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_dungeon_action_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="dungeon_action_attack"),
         InlineKeyboardButton(text="🏃‍♂️ Убежать", callback_data="dungeon_action_run")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "eco_dungeon")
async def cb_dungeon_menu(callback: CallbackQuery):
    text = "🔮 <b>Сюжетные Подземелья</b>\n\nЗдесь вы можете отправиться в экспедицию. Это опасно, но если у вас есть скрафченный <b>Меч</b> и <b>Броня</b>, ваши шансы выжить сильно возрастают!"
    await callback.message.edit_text(text, reply_markup=get_dungeon_start_kb())

@router.callback_query(F.data == "dungeon_enter_forest")
async def cb_dungeon_enter(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id

    async with db._conn.execute(
        'SELECT COUNT(*) FROM transactions WHERE sender_id = ? AND action_type = "dungeon_enter" AND timestamp > ?',
        (user_id, time.time() - 86400)
    ) as cursor:
        row = await cursor.fetchone()
        runs_today = row[0] if row else 0

    if runs_today >= 3:
        return await callback.answer("Вы уже совершили 3 экспедиции сегодня! Приходите завтра.", show_alert=True)

    if not await db.deduct_coins(user_id, 100):
        return await callback.answer("Вход в Лес стоит 100 🪙! У вас не хватает.", show_alert=True)

    await db.add_transaction(user_id, 0, 100, "dungeon_enter")
        
    scenarios = [
        "Вы идете по тропе и вдруг из кустов на вас выпрыгивает Дикий Гоблин! У него в руках ржавый нож.",
        "Ночь опустилась на лес. Вы слышите вой волков. Один из них преграждает вам путь, скаля зубы.",
        "Вы находите сундук, но когда тянетесь к нему, он отращивает зубы! Это Мимик!"
    ]
    
    text = "🌲 <b>Темный Лес</b>\n\n" + random.choice(scenarios) + "\n\nЧто вы будете делать?"
    await callback.message.edit_text(text, reply_markup=get_dungeon_action_kb())

@router.callback_query(F.data.startswith("dungeon_action_"))
async def cb_dungeon_action(callback: CallbackQuery, db: Database):
    action = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Check inventory: tuple is (id, user_id, item_type, item_value)
    inv = await db.get_user_inventory(user_id)
    has_sword = any(item[2] == "sword" for item in inv)
    has_armor = any(item[2] == "armor" for item in inv)
    
    base_win_chance = 30
    if has_sword: base_win_chance += 30
    if has_armor: base_win_chance += 20
    
    if action == "attack":
        roll = random.randint(1, 100)
        if roll <= base_win_chance:
            reward = random.randint(500, 1500)
            await db.add_coins(user_id, reward)
            text = f"⚔️ <b>Победа!</b>\n\nВы храбро сражались и одолели врага! "
            if has_sword: text += "(Ваш меч очень помог!). "
            text += f"\n\nВы нашли <b>{reward} 🪙</b>!"
        else:
            text = f"💀 <b>Поражение...</b>\n\nМонстр оказался сильнее. Вы чудом спаслись, но потеряли часть вещей."
            # Maybe deduct some coins
            pass
    else:
        # Run
        roll = random.randint(1, 100)
        if roll <= 70:
            text = "🏃‍♂️ Вы благополучно убежали. Награды нет, но вы целы."
        else:
            text = "🏃‍♂️ Вы попытались убежать, но споткнулись! Вы потеряли 50 🪙 во время бегства."
            await db.deduct_coins(user_id, 50)
            
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В Меню Игр", callback_data="cat_games")]]))
