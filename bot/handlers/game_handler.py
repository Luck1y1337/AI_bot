from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import Database
from bot.keyboards.inline_kb import get_quiz_kb, get_blackjack_kb, get_roulette_bet_kb, get_roulette_color_kb
from bot.fsm.states import BlackjackStates, RouletteStates
from aiogram.fsm.context import FSMContext
import random
from utils.achievements import ACHIEVEMENTS
router = Router()

from utils.quiz_data import QUESTIONS

async def get_next_quiz_question(state: FSMContext) -> dict:
    data = await state.get_data()
    history = data.get("quiz_history", [])
    
    available_indices = [i for i in range(len(QUESTIONS)) if i not in history]
    if not available_indices:
        history = []
        available_indices = list(range(len(QUESTIONS)))
        
    idx = random.choice(available_indices)
    history.append(idx)
    
    # Keep only last 40 questions in history to avoid memory bloat but prevent recent repeats
    if len(history) > 40:
        history.pop(0)
        
    await state.update_data(quiz_history=history)
    return QUESTIONS[idx]

@router.message(F.text.in_(["/quiz", "🎮 Играть (Quiz)"]))
async def cmd_quiz(message: Message, state: FSMContext):
    q = await get_next_quiz_question(state)
    await message.answer(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data == "eco_quiz")
async def cb_eco_quiz(callback: CallbackQuery, state: FSMContext):
    q = await get_next_quiz_question(state)
    await callback.message.edit_text(q["q"], reply_markup=get_quiz_kb(q["opts"], q["ans"]))

@router.callback_query(F.data.startswith("quiz_"))
async def process_quiz(callback: CallbackQuery, db: Database):
    is_correct = callback.data.split("_")[1] == "1"
    user = await db.get_user(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="eco_quiz")],
        [InlineKeyboardButton(text="🏠 Назад в Экономику", callback_data="back_to_economy")]
    ])
    
    if is_correct:
        user.xp += 10
        user.coins += 5
        user.trust = min(100, user.trust + 3)
        await db.update_user(user)
        await callback.message.edit_text("Хмпф. Ты правда ответил правильно. Неплохо. (+10 XP, +5 🪙)", reply_markup=kb)
        
        # Check quiz master
        if user.xp >= 100:
            current_achs = [a.achievement_type for a in await db.get_user_achievements(user.id)]
            if "quiz_master" not in current_achs:
                await db.add_achievement(user.id, "quiz_master")
                await callback.message.answer("🏆 Открыто достижение: Мастер Викторин!")
    else:
        await callback.message.edit_text("Бзззт! Неправильно. Ты вообще меня слушаешь?", reply_markup=kb)
    
    await callback.answer()

@router.message(F.text.in_(["/leaderboard", "🏆 Лидеры"]))
async def cmd_leaderboard(message: Message, db: Database):
    await _show_leaderboard(message, db)

@router.callback_query(F.data == "open_leaderboard")
async def cb_open_leaderboard(callback: CallbackQuery, db: Database):
    await _show_leaderboard(callback.message, db)
    await callback.answer()

async def _show_leaderboard(chat: Message, db: Database):
    from utils.levels import get_level, get_title
    top_users = await db.get_top_users_by_xp(10)
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b> 🏆\n━━━━━━━━━━━━━━\n\n"
    for i, u in enumerate(top_users):
        inventory = await db.get_user_inventory(u.id)
        titles = [item[3] for item in inventory if item[2] == 'title']
        title_text = f" [{titles[0]}]" if titles else ""
        medal = medals[i] if i < 3 else f"<code>{i+1}.</code>"
        display_name = f"@{u.username}" if u.username else f"ID {u.id}"
        lvl = get_level(u.xp)
        text += f"{medal}{title_text} {display_name} — Ур. {lvl} ({u.xp} XP)\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="main_hub")]])
    await chat.answer(text, reply_markup=kb)

@router.callback_query(F.data == "eco_blackjack")
async def cb_eco_blackjack(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BlackjackStates.waiting_for_bet)
    await callback.message.edit_text("🃏 <b>Блэкджек (21)</b>\n\nОбыграйте дилера, не набрав больше 21!\n\nВведите ставку (в коинах):")
    await callback.answer()

@router.callback_query(F.data == "roul_main")
async def cb_roul_main(callback: CallbackQuery):
    await callback.message.edit_text("🎡 <b>Рулетка</b>\n\nВыберите сумму ставки:", reply_markup=get_roulette_bet_kb())
    await callback.answer()

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
    await message.answer("🃏 <b>Блэкджек (21)</b>\nВведите вашу ставку (в коинах):")

@router.message(BlackjackStates.waiting_for_bet)
async def process_bj_bet(message: Message, state: FSMContext, db: Database):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите корректную ставку (число > 0).")
        return
        
    success = await db.deduct_coins(message.from_user.id, bet)
    if not success:
        await message.answer(f"У вас недостаточно коинов!")
        await state.clear()
        return
        
    deck = get_deck()
    random.shuffle(deck)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    await state.update_data(bet=bet, deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
    await state.set_state(BlackjackStates.playing)
    
    text = f"🃏 <b>Блэкджек</b> | Ставка: {bet} 🪙\n\n"
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
        winnings = int(bet * 2.5) # Original bet + 1.5x profit
        user.coins += winnings
        final_text = base_text + f"\n🎉 <b>Блэкджек! Вы выиграли {winnings - bet} 🪙!</b>"
    elif reason == "bust":
        final_text = base_text + f"\n💥 <b>Перебор! Вы проиграли {bet} 🪙.</b>"
    else:
        # Dealer plays
        while calculate_hand(d_hand) < 17:
            d_hand.append(deck.pop())
        d_score = calculate_hand(d_hand)
        
        final_text = f"🃏 <b>Блэкджек</b> | Ставка: {bet} 🪙\n\n"
        final_text += f"Ваша рука: {' '.join(p_hand)} (Сумма: {p_score})\n"
        final_text += f"Рука дилера: {' '.join(d_hand)} (Сумма: {d_score})\n\n"
        
        if d_score > 21 or p_score > d_score:
            user.coins += bet * 2
            final_text += f"🎉 <b>Вы выиграли {bet} 🪙!</b>"
        elif p_score < d_score:
            final_text += f"💸 <b>Дилер выиграл. Вы проиграли {bet} 🪙.</b>"
        else:
            user.coins += bet
            final_text += "🤝 <b>Ничья. Ставка возвращена.</b>"
            
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
        
        text = f"🃏 <b>Блэкджек</b> | Ставка: {data['bet']} 🪙\n\n"
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
async def cmd_roulette(message: Message):
    await message.answer("🎡 <b>Рулетка</b>\nВыберите сумму ставки:", reply_markup=get_roulette_bet_kb())

@router.callback_query(F.data.startswith("rl_bet_"))
async def cb_rl_bet(callback: CallbackQuery):
    bet = int(callback.data.split("_")[2])
    await callback.message.edit_text(f"🎡 <b>Рулетка</b>\nСтавка: <b>{bet} 🪙</b>\nВыберите цвет:", reply_markup=get_roulette_color_kb(bet))
    await callback.answer()

@router.callback_query(F.data.startswith("rl_color_"))
async def cb_rl_color(callback: CallbackQuery, db: Database):
    parts = callback.data.split("_")
    bet = int(parts[2])
    bet_type = parts[3]
    
    success = await db.deduct_coins(callback.from_user.id, bet)
    if not success:
        await callback.answer("Недостаточно средств для ставки!", show_alert=True)
        return
        
    await _process_roulette_result(callback, bet, bet_type, db)

async def _process_roulette_result(callback: CallbackQuery, bet: int, bet_type: str, db: Database):
    roll = random.randint(0, 36)
    if roll == 0:
        result_color = "green"
    elif roll in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        result_color = "red"
    else:
        result_color = "black"
        
    color_emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[result_color]
    text = f"🎡 Шарик остановился на: <b>{roll} {color_emoji}</b>\n\n"
    win = 0
    
    if bet_type == result_color:
        win = bet * 2 if result_color != "green" else bet * 14
        text += f"🎉 Вы угадали цвет! Выигрыш: {win} 🪙"
    else:
        text += f"💸 Ставка не сыграла. Вы потеряли {bet} 🪙."
        
    if win > 0:
        await db.add_coins(callback.from_user.id, win)
    
    from utils.quests import increment_quest_progress
    await increment_quest_progress(callback.from_user.id, "play_casino", 1, db)
    
    await callback.message.edit_text(text)

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
    except (ValueError, TypeError):
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
