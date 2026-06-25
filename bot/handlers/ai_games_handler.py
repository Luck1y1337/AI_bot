from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.repository import Database
from bot.fsm.states import AIGamesStates
from ai.mistral_client import MistralClient
from ai.prompt_builder import build_system_prompt
import random

router = Router()

def get_ai_games_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔢 Угадай Число", callback_data="ai_game_guess")],
        [InlineKeyboardButton(text="🔤 Игра в Города", callback_data="ai_game_words")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(F.text == "🤖 Игры с ИИ")
async def cmd_ai_games(message: Message):
    text = "🤖 **Игры с Махиро**\n\nВы можете сыграть с ИИ в интерактивные игры! Выберите во что поиграем:"
    await message.answer(text, reply_markup=get_ai_games_menu())

@router.callback_query(F.data == "ai_games_menu")
async def cb_ai_games(callback: CallbackQuery):
    text = "🤖 **Игры с Махиро**\n\nВы можете сыграть с ИИ в интерактивные игры! Выберите во что поиграем:"
    await callback.message.edit_text(text, reply_markup=get_ai_games_menu())
    await callback.answer()

@router.callback_query(F.data == "ai_game_guess")
async def cb_start_guess(callback: CallbackQuery, state: FSMContext):
    number = random.randint(1, 100)
    await state.set_state(AIGamesStates.playing_guess_number)
    await state.update_data(ai_guess_number=number, ai_guess_attempts=0)
    
    text = "🔢 **Угадай число (от 1 до 100)**\n\nЯ загадала число! Попробуй угадать его, отправляя мне числа в чат. Если хочешь сдаться, напиши 'отмена'."
    await callback.message.edit_text(text)

@router.message(AIGamesStates.playing_guess_number)
async def process_guess_number(message: Message, state: FSMContext, mistral: MistralClient, db: Database):
    if message.text.lower() in ['отмена', 'стоп', 'сдаюсь']:
        data = await state.get_data()
        await message.answer(f"Ты сдался! А я загадывала число {data['ai_guess_number']}.")
        await state.clear()
        return
        
    try:
        guess = int(message.text)
    except (ValueError, TypeError):
        await message.answer("Просто отправь мне число (или 'отмена' чтобы закончить).")
        return
        
    data = await state.get_data()
    secret = data['ai_guess_number']
    attempts = data['ai_guess_attempts'] + 1
    await state.update_data(ai_guess_attempts=attempts)
    
    user = await db.get_user(message.from_user.id)
    sys_prompt = build_system_prompt(user.mood, user.trust, [], {}, modifier="You are playing 'Guess the Number'. You generated a number. The user is guessing. Keep responses very short and snarky.")
    
    if guess == secret:
        prompt = f"The user correctly guessed the number {secret} in {attempts} attempts. Praise them slightly."
        user.trust += 5
        await db.update_user(user)
        resp = await mistral.generate_response([{"role": "user", "content": prompt}], sys_prompt)
        await message.answer(f"🎉 **Правильно!**\n\nМахиро: {resp}")
        await state.clear()
    elif guess < secret:
        prompt = f"The user guessed {guess}. The secret number is HIGHER. Tell them it's higher."
        resp = await mistral.generate_response([{"role": "user", "content": prompt}], sys_prompt)
        await message.answer(f"⬆️ Махиро: {resp}")
    else:
        prompt = f"The user guessed {guess}. The secret number is LOWER. Tell them it's lower."
        resp = await mistral.generate_response([{"role": "user", "content": prompt}], sys_prompt)
        await message.answer(f"⬇️ Махиро: {resp}")

@router.callback_query(F.data == "ai_game_words")
async def cb_start_words(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIGamesStates.playing_words)
    await state.update_data(ai_words_history=[])
    text = "🔤 **Игра в Города**\n\nЯ начну! Мой город: **Москва**.\nТеперь тебе нужно назвать город на букву 'А'. (Пиши 'отмена' чтобы сдаться)."
    await callback.message.edit_text(text)
    await state.update_data(ai_last_letter='а', ai_words_history=['москва'])

@router.message(AIGamesStates.playing_words)
async def process_words(message: Message, state: FSMContext, mistral: MistralClient, db: Database):
    if message.text.lower() in ['отмена', 'стоп', 'сдаюсь']:
        await message.answer("Сдаешься? Эх ты, слабак. Я победила!")
        await state.clear()
        return
        
    city = message.text.strip().lower()
    data = await state.get_data()
    expected_letter = data.get('ai_last_letter')
    history = data.get('ai_words_history', [])
    
    if not city.startswith(expected_letter):
        await message.answer(f"Эй, город должен начинаться на букву '{expected_letter.upper()}'!")
        return
        
    if city in history:
        await message.answer("Этот город уже был! Придумай другой.")
        return
        
    # Get last valid letter of user's city
    last_char = city[-1]
    if last_char in ['ь', 'ъ', 'ы']:
        last_char = city[-2]
        
    history.append(city)
    
    user = await db.get_user(message.from_user.id)
    sys_prompt = build_system_prompt(user.mood, user.trust, [], {}, modifier=f"You are playing 'City Names' game. The user said a city ending with {last_char}. You must name a REAL city starting with {last_char}. ONLY say the city name, nothing else.")
    
    # Let AI think of a city
    ai_city_raw = await mistral.generate_response([{"role": "user", "content": f"Your turn! Name a city starting with '{last_char}'"}], sys_prompt)
    ai_city = ai_city_raw.strip().lower()
    
    # Strip punctuation if AI added it
    import re
    ai_city = re.sub(r'[^\w\s]', '', ai_city)
    
    if not ai_city or len(ai_city) < 2:
        await message.answer("Ух... я не могу вспомнить город. Ты победил! (+5 Доверия)")
        user.trust += 5
        await db.update_user(user)
        await state.clear()
        return
        
    history.append(ai_city)
    
    ai_last_char = ai_city[-1]
    if ai_last_char in ['ь', 'ъ', 'ы']:
        ai_last_char = ai_city[-2]
        
    await state.update_data(ai_words_history=history, ai_last_letter=ai_last_char)
    await message.answer(f"Мой ответ: **{ai_city.capitalize()}**!\nТебе на букву '{ai_last_char.upper()}'")
