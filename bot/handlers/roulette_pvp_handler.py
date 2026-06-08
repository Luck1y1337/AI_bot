from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import asyncio

router = Router()

ROULETTE_LOBBIES = {}

def get_roulette_main_kb(active_lobbies=None) -> InlineKeyboardMarkup:
    kb = []
    if active_lobbies:
        for lid in active_lobbies:
            kb.append([InlineKeyboardButton(text=f"🔫 Присоединиться к Лобби #{lid}", callback_data=f"roul_join_{lid}")])
            
    kb.extend([
        [InlineKeyboardButton(text="🔫 Создать Лобби (1000 🪙)", callback_data="roul_create_1000")],
        [InlineKeyboardButton(text="🔫 Создать Лобби (5000 🪙)", callback_data="roul_create_5000")],
        [InlineKeyboardButton(text="🔫 Создать Лобби (10000 🪙)", callback_data="roul_create_10000")],
        [InlineKeyboardButton(text="👀 Обновить список", callback_data="roul_refresh")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_games")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_lobby_kb(lobby_id: str, is_owner: bool) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="➕ Присоединиться", callback_data=f"roul_join_{lobby_id}")]
    ]
    if is_owner:
        kb.append([InlineKeyboardButton(text="▶️ Начать игру", callback_data=f"roul_start_{lobby_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Выйти в меню", callback_data="roul_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_game_kb(lobby_id: str, current_turn_id: int, user_id: int) -> InlineKeyboardMarkup:
    # Always return shoot button, but validate in callback
    kb = [[InlineKeyboardButton(text="💥 ЖАТЬ НА КУРОК!", callback_data=f"roul_shoot_{lobby_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "roul_main")
@router.callback_query(F.data == "roul_refresh")
async def cb_roulette_main(callback: CallbackQuery):
    text = "🔫 **Русская Рулетка (Мультиплеер)**\n\nСмертельная игра до последнего выжившего. Победитель забирает весь банк!\n\n**Активные Лобби:**\n"
    
    active_lobbies = [k for k, v in ROULETTE_LOBBIES.items() if v["status"] == "waiting"]
    if not active_lobbies:
        text += "Нет активных лобби. Создайте свое!"
    else:
        for lid in active_lobbies:
            l = ROULETTE_LOBBIES[lid]
            text += f"\nЛобби #{lid} | Ставка: {l['bet']} 🪙 | Игроков: {len(l['players'])}/6"
            
    await callback.message.edit_text(text, reply_markup=get_roulette_main_kb(active_lobbies))
    if callback.data == "roul_refresh":
        await callback.answer("Обновлено.")

@router.callback_query(F.data.startswith("roul_create_"))
async def cb_roul_create(callback: CallbackQuery, db: Database):
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    for l in ROULETTE_LOBBIES.values():
        if user_id in l["players"] and l["status"] != "finished":
            return await callback.answer("Вы уже находитесь в лобби!", show_alert=True)
            
    if not await db.deduct_coins(user_id, bet):
        return await callback.answer("У вас недостаточно коинов!", show_alert=True)
        
    lobby_id = str(random.randint(1000, 9999))
    ROULETTE_LOBBIES[lobby_id] = {
        "owner": user_id,
        "bet": bet,
        "players": [user_id],
        "status": "waiting"
    }
    
    text = f"🔫 **Лобби #{lobby_id}**\n\nСтавка: {bet} 🪙\nИгроки (1/6):\n1. {user_id} (Хост)\n\nОжидание других игроков..."
    await callback.message.edit_text(text, reply_markup=get_lobby_kb(lobby_id, True))
    await callback.answer("Лобби создано!")

@router.callback_query(F.data.startswith("roul_join_"))
async def cb_roul_join(callback: CallbackQuery, db: Database):
    lobby_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if lobby_id not in ROULETTE_LOBBIES:
        return await callback.answer("Лобби не существует!", show_alert=True)
        
    lobby = ROULETTE_LOBBIES[lobby_id]
    if lobby["status"] != "waiting":
        return await callback.answer("Игра уже началась!", show_alert=True)
        
    if len(lobby["players"]) >= 6:
        return await callback.answer("Лобби заполнено!", show_alert=True)
        
    if user_id in lobby["players"]:
        return await callback.answer("Вы уже в этом лобби!", show_alert=True)
        
    for l in ROULETTE_LOBBIES.values():
        if user_id in l["players"] and l["status"] != "finished":
            return await callback.answer("Вы уже находитесь в другом лобби!", show_alert=True)
            
    if not await db.deduct_coins(user_id, lobby["bet"]):
        return await callback.answer("У вас недостаточно коинов!", show_alert=True)
        
    lobby["players"].append(user_id)
    
    text = f"🔫 **Лобби #{lobby_id}**\n\nСтавка: {lobby['bet']} 🪙\nИгроки ({len(lobby['players'])}/6):\n"
    for i, p in enumerate(lobby["players"], 1):
        text += f"{i}. {p}\n"
        
    text += "\nОжидание..."
    await callback.message.edit_text(text, reply_markup=get_lobby_kb(lobby_id, lobby["owner"] == user_id))
    await callback.answer("Вы присоединились!")

@router.callback_query(F.data.startswith("roul_start_"))
async def cb_roul_start(callback: CallbackQuery):
    lobby_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if lobby_id not in ROULETTE_LOBBIES:
        return await callback.answer("Лобби не существует!", show_alert=True)
        
    lobby = ROULETTE_LOBBIES[lobby_id]
    if lobby["owner"] != user_id:
        return await callback.answer("Только создатель может начать игру!", show_alert=True)
        
    if len(lobby["players"]) < 2:
        return await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
        
    lobby["status"] = "playing"
    lobby["turn_idx"] = 0
    lobby["bullet_pos"] = random.randint(0, 5)
    lobby["current_chamber"] = 0
    lobby["total_bank"] = lobby["bet"] * len(lobby["players"])
    lobby["msg_ids"] = [] # We'll just update the main message
    
    current_player = lobby["players"][0]
    
    text = f"🔫 **ИГРА НАЧАЛАСЬ!** Лобби #{lobby_id}\nБанк: {lobby['total_bank']} 🪙\n\n"
    text += f"Револьвер заряжен 1 патроном из 6. Барабан раскручен.\n\n"
    text += f"💥 Ход игрока: {current_player}"
    
    await callback.message.edit_text(text, reply_markup=get_game_kb(lobby_id, current_player, user_id))

@router.callback_query(F.data.startswith("roul_shoot_"))
async def cb_roul_shoot(callback: CallbackQuery, db: Database, bot: Bot):
    lobby_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if lobby_id not in ROULETTE_LOBBIES:
        return await callback.answer("Лобби не найдено", show_alert=True)
        
    lobby = ROULETTE_LOBBIES[lobby_id]
    if lobby["status"] != "playing":
        return await callback.answer("Игра не активна!", show_alert=True)
        
    current_player = lobby["players"][lobby["turn_idx"]]
    
    if user_id != current_player:
        return await callback.answer(f"Сейчас ход игрока {current_player}!", show_alert=True)
        
    is_dead = (lobby["current_chamber"] == lobby["bullet_pos"])
    
    if is_dead:
        await callback.answer("ВЫСТРЕЛ! Вы убиты... 💀", show_alert=True)
        lobby["players"].pop(lobby["turn_idx"])
        lobby["bullet_pos"] = random.randint(0, 5)
        lobby["current_chamber"] = 0
        if lobby["turn_idx"] >= len(lobby["players"]):
            lobby["turn_idx"] = 0
    else:
        await callback.answer("Щелчок. Вы выжили! 😌", show_alert=True)
        lobby["current_chamber"] += 1
        lobby["turn_idx"] = (lobby["turn_idx"] + 1) % len(lobby["players"])
        
    # Check win condition
    if len(lobby["players"]) == 1:
        winner = lobby["players"][0]
        bank = lobby["total_bank"]
        tax = int(bank * 0.05)
        win_amount = bank - tax
        await db.add_coins(winner, win_amount)
        
        lobby["status"] = "finished"
        text = f"🏆 **ИГРА ОКОНЧЕНА!** Лобби #{lobby_id}\n\nПоследний выживший: {winner}\nОн забирает {win_amount} 🪙 (Налог: {tax} 🪙)!"
        active_lobbies = [k for k, v in ROULETTE_LOBBIES.items() if v["status"] == "waiting"]
        await callback.message.edit_text(text, reply_markup=get_roulette_main_kb(active_lobbies))
        # Clean up later or leave it to be overwritten
    else:
        next_player = lobby["players"][lobby["turn_idx"]]
        text = f"🔫 **ИГРА ИДЕТ!** Лобби #{lobby_id}\nБанк: {lobby['total_bank']} 🪙\n\n"
        if is_dead:
            text += f"💀 Игрок {user_id} застрелился!\nБарабан раскручен заново.\n\n"
        else:
            text += f"😌 Игрок {user_id} выжил (щелчок).\n\n"
            
        text += f"💥 Ход игрока: {next_player}"
        await callback.message.edit_text(text, reply_markup=get_game_kb(lobby_id, next_player, user_id))
