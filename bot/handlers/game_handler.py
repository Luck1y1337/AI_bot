from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.repository import Database
from bot.keyboards.inline_kb import get_quiz_kb, get_blackjack_kb
from bot.fsm.states import BlackjackStates, RouletteStates
from aiogram.fsm.context import FSMContext
import random
from utils.achievements import ACHIEVEMENTS

router = Router()

import json
from ai.mistral_client import MistralClient

async def generate_ai_quiz(mistral: MistralClient) -> dict:
    sys_prompt = "You are a quiz generator. Return ONLY valid JSON format. No markdown, no extra text. The JSON must have exactly: 'q' (the question string, in Russian, topic: anime, video games, or Mahiro Oyama trivia), 'opts' (array of exactly 4 strings with options in Russian), and 'ans' (integer 0-3 for the correct option index)."
    prompt = "Сгенерируй случайный вопрос для викторины."
    try:
        response = await mistral.generate_response(prompt, sys_prompt)
        response = response.replace('```json', '').replace('```', '').strip()
        data = json.loads(response)
        if "q" in data and "opts" in data and "ans" in data and len(data["opts"]) == 4:
            return data
    except Exception:
        pass
    
    return {"q": "Ошибка генерации. Кто я?", "opts": ["Махиро", "Михари", "Каэде", "Момидзи"], "ans": 0}

@router.message(F.text.in_(["/quiz", "🎮 Играть (Quiz)"]))
async def cmd_quiz(message: Message, mistral: MistralClient):
    msg = await message.answer("Генерирую уникальный вопрос... ⏳")
    q = await generate_ai_quiz(mistral)
    await msg.edit_text(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data == "eco_quiz")
async def cb_eco_quiz(callback: CallbackQuery, mistral: MistralClient):
    await callback.message.edit_text("Генерирую уникальный вопрос... ⏳")
    q = await generate_ai_quiz(mistral)
    await callback.message.edit_text(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data.startswith("quiz_"))
async def process_quiz(callback: CallbackQuery, db: Database):
    is_correct = callback.data.split("_")[1] == "1"
    user = await db.get_user(callback.from_user.id)
    
    if is_correct:
        user.xp += 10
        user.coins += 5
        user.trust = min(100, user.trust + 3)
        await db.update_user(user)
        await callback.message.edit_text("Хмпф. Ты правда ответил правильно. Неплохо. (+10 XP, +5 🪙)")
        
        # Check quiz master
        if user.xp >= 100:
            current_achs = [a.achievement_type for a in await db.get_user_achievements(user.id)]
            if "quiz_master" not in current_achs:
                await db.add_achievement(user.id, "quiz_master")
                await callback.message.answer("🏆 Открыто достижение: Мастер Викторин!")
    else:
        await callback.message.edit_text("Бзззт! Неправильно. Ты вообще меня слушаешь?")
    
    await callback.answer()

@router.message(F.text.in_(["/leaderboard", "🏆 Лидеры"]))
async def cmd_leaderboard(message: Message, db: Database):
    top_users = await db.get_top_users_by_xp(10)
    text = "🏆 **Таблица Лидеров (XP)** 🏆\n\n"
    for i, u in enumerate(top_users):
        inventory = await db.get_user_inventory(u.id)
        titles = [item[3] for item in inventory if item[2] == 'title']
        title_text = f" [{titles[0]}]" if titles else ""
        
        display_name = f"@{u.username}" if u.username else f"ID {u.id}"
        text += f"{i+1}.{title_text} {display_name} - {u.xp} XP\n"
    await message.answer(text)

# --- Блэкджек (21) ---
def get_deck():
    suits = ['♠️', '♥️', '♦️', '♣️']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    return [f"{r}{s}" for s in suits for r in ranks]

def calculate_hand(hand: list) -> int:
    value = 0
    aces = 0
    for card in hand:
        rank = card[:-2]
        if rank in ['J', 'Q', 'K']:
            value += 10
        elif rank == 'A':
            aces += 1
            value += 11
        else:
            value += int(rank)
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

@router.message(F.text.lower() == "блэкджек")
async def cmd_blackjack(message: Message, state: FSMContext):
    await state.set_state(BlackjackStates.waiting_for_bet)
    await message.answer("🃏 **Блэкджек (21)**\nВведите вашу ставку (в коинах):")

@router.message(BlackjackStates.waiting_for_bet)
async def process_bj_bet(message: Message, state: FSMContext, db: Database):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
    except:
        await message.answer("Пожалуйста, введите корректную ставку (число > 0).")
        return
        
    user = await db.get_user(message.from_user.id)
    if user.coins < bet:
        await message.answer(f"У вас недостаточно коинов! Ваш баланс: {user.coins} 🪙")
        await state.clear()
        return
        
    deck = get_deck()
    random.shuffle(deck)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    await state.update_data(bet=bet, deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
    await state.set_state(BlackjackStates.playing)
    
    text = f"🃏 **Блэкджек** | Ставка: {bet} 🪙\n\n"
    text += f"Ваша рука: {' '.join(player_hand)} (Сумма: {calculate_hand(player_hand)})\n"
    text += f"Рука дилера: {dealer_hand[0]} 🎴 (Сумма: ?)\n"
    
    if calculate_hand(player_hand) == 21:
        await finish_bj(message, state, db, text, "blackjack")
    else:
        await message.answer(text, reply_markup=get_blackjack_kb())

async def finish_bj(message_or_call, state: FSMContext, db: Database, base_text: str, reason: str):
    data = await state.get_data()
    bet = data['bet']
    p_hand = data['player_hand']
    d_hand = data['dealer_hand']
    deck = data['deck']
    
    p_score = calculate_hand(p_hand)
    
    user_id = message_or_call.from_user.id
    is_call = isinstance(message_or_call, CallbackQuery)
    user = await db.get_user(user_id)
    
    if reason == "blackjack":
        winnings = int(bet * 1.5)
        user.coins += winnings
        final_text = base_text + f"\n🎉 **Блэкджек! Вы выиграли {winnings} 🪙!**"
    elif reason == "bust":
        user.coins -= bet
        final_text = base_text + f"\n💥 **Перебор! Вы проиграли {bet} 🪙.**"
    else:
        # Dealer plays
        while calculate_hand(d_hand) < 17:
            d_hand.append(deck.pop())
        d_score = calculate_hand(d_hand)
        
        final_text = f"🃏 **Блэкджек** | Ставка: {bet} 🪙\n\n"
        final_text += f"Ваша рука: {' '.join(p_hand)} (Сумма: {p_score})\n"
        final_text += f"Рука дилера: {' '.join(d_hand)} (Сумма: {d_score})\n\n"
        
        if d_score > 21 or p_score > d_score:
            user.coins += bet
            final_text += f"🎉 **Вы выиграли {bet} 🪙!**"
        elif p_score < d_score:
            user.coins -= bet
            final_text += f"💸 **Дилер выиграл. Вы проиграли {bet} 🪙.**"
        else:
            final_text += "🤝 **Ничья. Ставка возвращена.**"
            
    await db.update_user(user)
    await state.clear()
    
    if is_call:
        await message_or_call.message.edit_text(final_text)
    else:
        await message_or_call.answer(final_text)

@router.callback_query(BlackjackStates.playing)
async def cb_bj_action(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    p_hand = data['player_hand']
    deck = data['deck']
    
    if callback.data == "bj_hit":
        p_hand.append(deck.pop())
        await state.update_data(player_hand=p_hand, deck=deck)
        
        p_score = calculate_hand(p_hand)
        d_hand = data['dealer_hand']
        
        text = f"🃏 **Блэкджек** | Ставка: {data['bet']} 🪙\n\n"
        text += f"Ваша рука: {' '.join(p_hand)} (Сумма: {p_score})\n"
        text += f"Рука дилера: {d_hand[0]} 🎴 (Сумма: ?)\n"
        
        if p_score > 21:
            await finish_bj(callback, state, db, text, "bust")
        elif p_score == 21:
            await finish_bj(callback, state, db, text, "stand")
        else:
            await callback.message.edit_text(text, reply_markup=get_blackjack_kb())
            
    elif callback.data == "bj_stand":
        await finish_bj(callback, state, db, "", "stand")
        
    await callback.answer()

# --- Рулетка ---
@router.message(F.text.lower() == "рулетка")
async def cmd_roulette(message: Message, state: FSMContext):
    await state.set_state(RouletteStates.waiting_for_bet)
    await message.answer("🎡 **Рулетка**\nВведите вашу ставку в формате: `<сумма> <цвет/число>`\nНапример: `100 red`, `50 black`, `20 green` или `10 7`")

@router.message(F.text.lower().startswith("roulette") | F.text.lower().startswith("рулетка "))
async def process_roulette_fast(message: Message, db: Database):
    # For fast betting like "рулетка 100 red"
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: рулетка <сумма> <цвет/число>")
        return
    await process_roulette_bet_internal(message, parts[1], parts[2], db)

@router.message(RouletteStates.waiting_for_bet)
async def process_roulette_bet(message: Message, state: FSMContext, db: Database):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: <сумма> <цвет/число>. Например: 100 red")
        return
    await process_roulette_bet_internal(message, parts[0], parts[1], db)
    await state.clear()

async def process_roulette_bet_internal(message: Message, amount_str: str, bet_type: str, db: Database):
    try:
        bet = int(amount_str)
        if bet <= 0: raise ValueError
    except:
        await message.answer("Некорректная сумма ставки.")
        return
        
    user = await db.get_user(message.from_user.id)
    if user.coins < bet:
        await message.answer(f"Недостаточно коинов! Ваш баланс: {user.coins} 🪙")
        return
        
    user.coins -= bet
    
    # Spin roulette
    result_num = random.randint(0, 36)
    if result_num == 0:
        result_color = "green"
    elif result_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        result_color = "red"
    else:
        result_color = "black"
        
    color_emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[result_color]
    text = f"🎡 Шарик остановился на: **{result_num} {color_emoji}**\n\n"
    
    bet_type = bet_type.lower()
    if bet_type == result_color:
        win = bet * 2 if result_color != "green" else bet * 14
        user.coins += win
        text += f"🎉 Вы угадали цвет! Выигрыш: {win} 🪙"
    elif bet_type.isdigit() and int(bet_type) == result_num:
        win = bet * 36
        user.coins += win
        text += f"🎰 ДЖЕКПОТ! Вы угадали число! Выигрыш: {win} 🪙"
    else:
        text += f"💸 Ставка не сыграла. Вы потеряли {bet} 🪙."
        
    await db.update_user(user)
    await message.answer(text)

# --- Камень Ножницы Бумага ---
@router.message(F.text.lower().startswith("кнб ") | F.text.lower().startswith("rps "))
async def cmd_rps(message: Message, db: Database):
    parts = message.text.lower().split()
    if len(parts) != 3:
        await message.answer("Использование: кнб <ставка> <камень/ножницы/бумага>")
        return
        
    try:
        bet = int(parts[1])
        if bet <= 0: raise ValueError
    except:
        await message.answer("Некорректная ставка.")
        return
        
    choice_map = {
        "камень": "rock", "rock": "rock", "к": "rock",
        "ножницы": "scissors", "scissors": "scissors", "н": "scissors",
        "бумага": "paper", "paper": "paper", "б": "paper"
    }
    
    player_choice = choice_map.get(parts[2])
    if not player_choice:
        await message.answer("Неверный выбор. Доступно: камень (к), ножницы (н), бумага (б).")
        return
        
    user = await db.get_user(message.from_user.id)
    if user.coins < bet:
        await message.answer(f"Недостаточно коинов. Ваш баланс: {user.coins} 🪙")
        return
        
    bot_choice = random.choice(["rock", "scissors", "paper"])
    emojis = {"rock": "🪨", "scissors": "✂️", "paper": "📄"}
    
    text = f"Вы выбрали {emojis[player_choice]}, Махиро выбрала {emojis[bot_choice]}.\n\n"
    
    if player_choice == bot_choice:
        text += "🤝 Ничья! Коины возвращены."
    elif (player_choice == "rock" and bot_choice == "scissors") or \
         (player_choice == "scissors" and bot_choice == "paper") or \
         (player_choice == "paper" and bot_choice == "rock"):
        user.coins += bet
        text += f"🎉 Вы победили! Выигрыш: {bet} 🪙"
    else:
        user.coins -= bet
        text += f"💸 Махиро победила! Вы проиграли {bet} 🪙"
        
    await db.update_user(user)
    await message.answer(text)
