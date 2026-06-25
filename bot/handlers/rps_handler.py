from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
import random
import asyncio

router = Router()

RPS_LOBBIES = {}

def get_rps_main_kb(active_lobbies=None) -> InlineKeyboardMarkup:
    kb = []
    if active_lobbies:
        for lid in active_lobbies:
            kb.append([InlineKeyboardButton(text=f"⚔️ Присоединиться к Лобби #{lid}", callback_data=f"rps_join_{lid}")])
            
    kb.extend([
        [InlineKeyboardButton(text="✂️ Создать Лобби (500 🪙)", callback_data="rps_create_500")],
        [InlineKeyboardButton(text="✂️ Создать Лобби (2000 🪙)", callback_data="rps_create_2000")],
        [InlineKeyboardButton(text="👀 Обновить список", callback_data="rps_refresh")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="eco_games")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rps_join_kb(lobby_id: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="⚔️ Присоединиться", callback_data=f"rps_join_{lobby_id}")],
        [InlineKeyboardButton(text="🔙 Выйти в меню", callback_data="rps_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rps_play_kb(lobby_id: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🪨 Камень", callback_data=f"rps_pick_{lobby_id}_rock"),
         InlineKeyboardButton(text="✂️ Ножницы", callback_data=f"rps_pick_{lobby_id}_scissors"),
         InlineKeyboardButton(text="📄 Бумага", callback_data=f"rps_pick_{lobby_id}_paper")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "rps_main")
@router.callback_query(F.data == "rps_refresh")
async def cb_rps_main(callback: CallbackQuery):
    text = "✌️ **Камень-Ножницы-Бумага (PvP)**\n\nКлассическая дуэль на коины!\n\n**Активные Лобби:**\n"
    
    active_lobbies = [k for k, v in RPS_LOBBIES.items() if v["status"] == "waiting"]
    if not active_lobbies:
        text += "Нет активных лобби."
    else:
        for lid in active_lobbies:
            l = RPS_LOBBIES[lid]
            text += f"\nЛобби #{lid} | Ставка: {l['bet']} 🪙 | Создатель: {l['p1']}"
            
    await callback.message.edit_text(text, reply_markup=get_rps_main_kb(active_lobbies))
    if callback.data == "rps_refresh":
        await callback.answer("Обновлено.")

@router.callback_query(F.data.startswith("rps_create_"))
async def cb_rps_create(callback: CallbackQuery, db: Database):
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    if bet > 100000:
        return await callback.answer("Максимальная ставка: 100,000 🪙!", show_alert=True)
    
    for l in RPS_LOBBIES.values():
        if l["p1"] == user_id or l.get("p2") == user_id:
            if l["status"] != "finished":
                return await callback.answer("Вы уже в игре!", show_alert=True)
                
    if not await db.deduct_coins(user_id, bet):
        return await callback.answer("У вас недостаточно коинов!", show_alert=True)
        
    lobby_id = str(random.randint(1000, 9999))
    RPS_LOBBIES[lobby_id] = {
        "p1": user_id,
        "p1_choice": None,
        "p2": None,
        "p2_choice": None,
        "bet": bet,
        "status": "waiting"
    }
    
    text = f"✌️ **Лобби #{lobby_id}**\n\nСтавка: {bet} 🪙\nСоздатель: {user_id}\n\nОжидание второго игрока..."
    await callback.message.edit_text(text, reply_markup=get_rps_join_kb(lobby_id))
    await callback.answer("Лобби создано!")

@router.callback_query(F.data.startswith("rps_join_"))
async def cb_rps_join(callback: CallbackQuery, db: Database):
    lobby_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if lobby_id not in RPS_LOBBIES:
        return await callback.answer("Лобби не существует!", show_alert=True)
        
    lobby = RPS_LOBBIES[lobby_id]
    if lobby["status"] != "waiting":
        return await callback.answer("Игра уже началась!", show_alert=True)
        
    if lobby["p1"] == user_id:
        return await callback.answer("Вы не можете играть сами с собой!", show_alert=True)
        
    for l in RPS_LOBBIES.values():
        if (l["p1"] == user_id or l.get("p2") == user_id) and l["status"] != "finished":
            return await callback.answer("Вы уже в игре!", show_alert=True)
            
    if not await db.deduct_coins(user_id, lobby["bet"]):
        return await callback.answer("У вас недостаточно коинов!", show_alert=True)
        
    lobby["p2"] = user_id
    lobby["status"] = "playing"
    
    text = f"✌️ **Лобби #{lobby_id}**\n\nИгрок 1: {lobby['p1']}\nИгрок 2: {lobby['p2']}\nСтавка: {lobby['bet']} 🪙\n\nВыберите ваш ход!"
    await callback.message.edit_text(text, reply_markup=get_rps_play_kb(lobby_id))
    await callback.answer("Вы присоединились!")

@router.callback_query(F.data.startswith("rps_pick_"))
async def cb_rps_pick(callback: CallbackQuery, db: Database):
    parts = callback.data.split("_")
    lobby_id = parts[2]
    choice = parts[3]
    user_id = callback.from_user.id
    
    if lobby_id not in RPS_LOBBIES:
        return await callback.answer("Лобби не существует!", show_alert=True)
        
    lobby = RPS_LOBBIES[lobby_id]
    if lobby["status"] != "playing":
        return await callback.answer("Игра не активна!", show_alert=True)
        
    if user_id == lobby["p1"]:
        if lobby["p1_choice"]: return await callback.answer("Вы уже сделали ход!", show_alert=True)
        lobby["p1_choice"] = choice
    elif user_id == lobby["p2"]:
        if lobby["p2_choice"]: return await callback.answer("Вы уже сделали ход!", show_alert=True)
        lobby["p2_choice"] = choice
    else:
        return await callback.answer("Вы не в этой игре!", show_alert=True)
        
    await callback.answer("Ход принят!")
    
    if lobby["p1_choice"] and lobby["p2_choice"]:
        lobby["status"] = "finished"
        c1, c2 = lobby["p1_choice"], lobby["p2_choice"]
        u1, u2 = lobby["p1"], lobby["p2"]
        bet = lobby["bet"]
        
        emojis = {"rock": "🪨", "scissors": "✂️", "paper": "📄"}
        text = f"✌️ **РЕЗУЛЬТАТЫ Лобби #{lobby_id}**\n\nИгрок {u1} выбрал: {emojis[c1]}\nИгрок {u2} выбрал: {emojis[c2]}\n\n"
        
        win_matrix = {
            "rock": "scissors",
            "scissors": "paper",
            "paper": "rock"
        }
        
        if c1 == c2:
            text += "Ничья! Ставки возвращены."
            await db.add_coins(u1, bet)
            await db.add_coins(u2, bet)
        elif win_matrix[c1] == c2:
            tax = int(bet * 0.05)
            win_amount = (bet * 2) - tax
            text += f"🏆 Игрок {u1} победил и забрал {win_amount} 🪙 (Налог: {tax} 🪙)!"
            await db.add_coins(u1, win_amount)
            await db.add_transaction(u2, u1, win_amount, "rps_win")
        else:
            tax = int(bet * 0.05)
            win_amount = (bet * 2) - tax
            text += f"🏆 Игрок {u2} победил и забрал {win_amount} 🪙 (Налог: {tax} 🪙)!"
            await db.add_coins(u2, win_amount)
            await db.add_transaction(u1, u2, win_amount, "rps_win")
            
        # Clean up finished lobbies to prevent memory leak
        finished = [k for k, v in RPS_LOBBIES.items() if v["status"] == "finished"]
        for k in finished:
            del RPS_LOBBIES[k]

        active_lobbies = [k for k, v in RPS_LOBBIES.items() if v["status"] == "waiting"]
        await callback.message.edit_text(text, reply_markup=get_rps_main_kb(active_lobbies))
    else:
        # One player has chosen, wait for other
        text = f"✌️ **Лобби #{lobby_id}**\n\nОдин из игроков уже сделал выбор!\nЖдем второго..."
        await callback.message.edit_text(text, reply_markup=get_rps_play_kb(lobby_id))
