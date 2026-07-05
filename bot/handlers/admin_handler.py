from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.text_decorations import html_decoration
from database.repository import Database
from config.settings import get_settings
from bot.fsm.states import AdminStates
from bot.keyboards.admin_kb import get_admin_main_kb, get_settings_menu, get_back_button, get_whitelist_menu, get_blacklist_menu, get_users_selection_kb
from media.charts import generate_activity_chart
import psutil
import platform
import os
import zipfile
import csv
import json
from memory.memory_manager import MemoryManager

router = Router()
settings = get_settings()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_USER_IDS

@router.message(F.text.in_(["/admin", "👑 Админ Панель"]))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ Панель", reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_promo_create")
async def cb_admin_promo_create(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_promo_data)
    await callback.message.edit_text("Отправьте данные для промокода в формате:\n<code>НАЗВАНИЕ КОИНЫ XP КОЛ-ВО</code>\n\nПример: <code>MAHIRO_GIFT 500 10 100</code>")
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_data)
async def process_promo_data(message: Message, state: FSMContext, db: Database):
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("❌ Неверный формат. Попробуйте еще раз: <code>НАЗВАНИЕ КОИНЫ XP ИСПОЛЬЗОВАНИЯ</code>")
        return
        
    try:
        code = parts[0]
        coins = int(parts[1])
        xp = int(parts[2])
        uses = int(parts[3])
    except ValueError:
        await message.answer("❌ Коины, XP и количество использований должны быть числами!")
        return
        
    await db._conn.execute('INSERT OR REPLACE INTO promocodes (code, reward_coins, reward_xp, max_uses, current_uses) VALUES (?, ?, ?, ?, 0)',
                          (code, coins, xp, uses))
    await db._conn.commit()
    await message.answer(f"✅ Промокод <code>{html_decoration.quote(code)}</code> успешно создан!\nНаграда: {coins} 🪙, {xp} ✨\nИспользований: {uses}")
    await state.clear()

@router.callback_query(F.data == "admin_ban_menu")
async def cb_admin_ban_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔨 Забанить", callback_data="admin_ban_user"),
         InlineKeyboardButton(text="🕊 Разбанить", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")]
    ])
    await callback.message.edit_text("Меню блокировки пользователей:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_ban_user")
async def cb_admin_ban_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_ban_id)
    await callback.message.edit_text("Отправьте ID пользователя, которого нужно ЗАБАНИТЬ:")
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_id)
async def process_ban_id(message: Message, state: FSMContext, db: Database):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    await db._conn.execute('UPDATE users SET is_banned = 1 WHERE id = ?', (user_id,))
    await db._conn.commit()
    await message.answer(f"✅ Пользователь <code>{user_id}</code> забанен!")
    await state.clear()

@router.callback_query(F.data == "admin_unban_user")
async def cb_admin_unban_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_unban_id)
    await callback.message.edit_text("Отправьте ID пользователя, которого нужно РАЗБАНИТЬ:")
    await callback.answer()

@router.message(AdminStates.waiting_for_unban_id)
async def process_unban_id(message: Message, state: FSMContext, db: Database):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    await db._conn.execute('UPDATE users SET is_banned = 0 WHERE id = ?', (user_id,))
    await db._conn.commit()
    await message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен!")
    await state.clear()

@router.callback_query(F.data.startswith("wl_approve_"))
async def wl_approve(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    target_id = int(callback.data.split("_")[2])
    await db.add_to_whitelist(target_id)
    await callback.message.edit_text(f"{html_decoration.quote(callback.message.text)}\n\n✅ <b>ОДОБРЕНО</b> администратором.")
    try:
        await callback.bot.send_message(target_id, "🎉 Администратор одобрил вашу заявку!\nТеперь вы можете общаться со мной. Напишите /start")
    except Exception: pass
    await callback.answer()

@router.callback_query(F.data.startswith("wl_deny_"))
async def wl_deny(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    target_id = int(callback.data.split("_")[2])
    # Optionally add to blacklist, but for now just deny
    await callback.message.edit_text(f"{html_decoration.quote(callback.message.text)}\n\n❌ <b>ОТКЛОНЕНО</b> администратором.")
    try:
        await callback.bot.send_message(target_id, "❌ Администратор отклонил вашу заявку на доступ.")
    except Exception: pass
    await callback.answer()

@router.callback_query(F.data == "admin_main")
async def admin_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Админ Панель", reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    users.sort(key=lambda x: x.message_count, reverse=True)
    text = f"👥 ВСЕ ПОЛЬЗОВАТЕЛИ ({len(users)})\n\n"
    for user in users[:20]:
        text += f"ID: {user.id} | 💬 {user.message_count} | 🪙 {user.coins}\n"
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_main"))

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    total_msgs = sum(u.message_count for u in users)
    text = f"📊 <b>Статистика</b>\nПользователей: {len(users)}\nСообщений: {total_msgs}"
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_main"))

@router.callback_query(F.data == "admin_transactions")
async def admin_transactions(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    transactions = await db.get_transactions(30)
    if not transactions:
        await callback.message.edit_text("📜 История транзакций пуста.", reply_markup=get_back_button("admin_main"))
        return
        
    text = "📜 <b>Последние 30 транзакций</b>\n\n"
    from datetime import datetime
    for t in transactions:
        dt = datetime.fromtimestamp(t.timestamp).strftime('%Y-%m-%d %H:%M')
        if t.action_type == "daily_bonus":
            text += f"[{dt}] 📅 БОНУС: User {t.receiver_id} получил {t.amount} 🪙\n"
        elif t.action_type == "gacha_roll":
            text += f"[{dt}] 🎰 ГАЧА: User {t.sender_id} потратил {t.amount} 🪙\n"
        elif t.action_type == "user_transfer":
            text += f"[{dt}] 💸 ПЕРЕВОД: User {t.sender_id} -> User {t.receiver_id} ({t.amount} 🪙)\n"
        elif t.action_type == "admin_add":
            text += f"[{dt}] 👑 АДМИН: Выдано {t.amount} 🪙 юзеру {t.receiver_id}\n"
        elif t.action_type == "admin_remove":
            text += f"[{dt}] 👑 АДМИН: Забрано {t.amount} 🪙 у юзера {t.receiver_id}\n"
        else:
            text += f"[{dt}] ❓ OTHER: {t.amount} 🪙 ({t.action_type})\n"
            
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_main"))

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("⚙️ НАСТРОЙКИ БОТА\n\nВыберите действие:", reply_markup=get_settings_menu())

@router.callback_query(F.data == "admin_analytics")
async def admin_analytics(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    activity_data = await db.get_daily_activity()
    path = await generate_activity_chart(activity_data)
    await callback.message.answer_photo(FSInputFile(path))
    await callback.answer()

@router.callback_query(F.data == "admin_sysinfo")
async def admin_sysinfo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    text = f"💻 <b>Система</b>\nCPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%\nOS: {platform.system()}"
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_settings"))

@router.callback_query(F.data == "admin_export")
async def admin_export(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    
    os.makedirs("cache/export", exist_ok=True)
    csv_path = "cache/export/users.csv"
    json_path = "cache/export/users.json"
    zip_path = "cache/export/export.zip"
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "trust", "mood", "message_count", "xp"])
        for u in users:
            writer.writerow([u.id, u.trust, u.mood, u.message_count, u.xp])
            
    with open(json_path, 'w') as f:
        json.dump([u.__dict__ for u in users], f, indent=4)
        
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(csv_path, "users.csv")
        zf.write(json_path, "users.json")
        if os.path.exists("logs/mahiro.log"):
            zf.write("logs/mahiro.log", "mahiro.log")
            
    await callback.message.answer_document(FSInputFile(zip_path))
    await callback.answer()

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    if os.path.exists("logs/mahiro.log"):
        await callback.message.answer_document(FSInputFile("logs/mahiro.log"))
    else:
        await callback.answer("Файл логов не найден.")

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.edit_text("Отправьте сообщение для рассылки всем пользователям:", reply_markup=get_back_button("admin_main"))

@router.callback_query(F.data == "admin_coins")
async def admin_coins_start(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    await callback.message.edit_text("Выберите пользователя для изменения коинов:", reply_markup=get_users_selection_kb(users, "coin", 0))

@router.message(AdminStates.waiting_for_coin_amount)
async def process_coin_amount(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data.get("coin_user_id")
        user = await db.get_user(user_id)
        diff = amount - user.coins
        user.coins = amount
        await db.update_user(user)
        if diff > 0:
            await db.add_transaction(message.from_user.id, user_id, diff, "admin_add")
        elif diff < 0:
            await db.add_transaction(message.from_user.id, user_id, abs(diff), "admin_remove")
        await message.answer(f"Баланс пользователя {user_id} успешно изменен на {amount} 🪙.", reply_markup=get_back_button("admin_main"))
    except Exception:
        await message.answer("Пожалуйста, отправьте корректное число.", reply_markup=get_back_button("admin_main"))
    await state.clear()

@router.callback_query(F.data == "admin_xp")
async def admin_xp_start(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    await callback.message.edit_text("Выберите пользователя для изменения XP:", reply_markup=get_users_selection_kb(users, "xp", 0))

@router.message(AdminStates.waiting_for_xp_amount)
async def process_xp_amount(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data.get("xp_user_id")
        user = await db.get_user(user_id)
        user.xp = amount
        await db.update_user(user)
        await message.answer(f"XP пользователя {user_id} успешно изменен на {amount} ✨.", reply_markup=get_back_button("admin_main"))
    except Exception:
        await message.answer("Пожалуйста, отправьте корректное число.", reply_markup=get_back_button("admin_main"))
    await state.clear()

@router.callback_query(F.data == "admin_history")
async def admin_history_start(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    await callback.message.edit_text("Выберите пользователя для просмотра истории диалога:", reply_markup=get_users_selection_kb(users, "history", 0))

@router.callback_query(F.data.startswith("admin_userspage_"))
async def admin_userspage(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    action = parts[2]
    page = int(parts[3])
    users = await db.get_all_users()
    text = f"Выберите пользователя для: {action}"
    await callback.message.edit_text(text, reply_markup=get_users_selection_kb(users, action, page))

@router.callback_query(F.data.startswith("admin_selectuser_"))
async def admin_selectuser(callback: CallbackQuery, state: FSMContext, db: Database, memory: MemoryManager):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    action = parts[2]
    user_id = int(parts[3])
    
    if action == "history":
        history = memory.short.get_history(user_id)
        if not history:
            await callback.message.edit_text(f"История для {user_id} пуста.", reply_markup=get_back_button("admin_main"))
        else:
            text = f"💬 <b>История для {user_id}:</b>\n\n"
            for msg in history:
                icon = "👤" if msg['role'] == "user" else "🤖"
                text += f"{icon} {html_decoration.quote(msg['content'])}\n"
                if len(text) > 3500:
                    text += "...\n[Сообщение обрезано из-за лимита Telegram]"
                    break
            await callback.message.edit_text(text, reply_markup=get_back_button("admin_main"))
    elif action == "coin":
        user = await db.get_user(user_id)
        await state.update_data(coin_user_id=user_id)
        await state.set_state(AdminStates.waiting_for_coin_amount)
        await callback.message.edit_text(f"Выбран пользователь {user_id}.\nТекущий баланс: {user.coins} 🪙.\nОтправьте новое количество коинов:", reply_markup=get_back_button("admin_main"))
    elif action == "xp":
        user = await db.get_user(user_id)
        await state.update_data(xp_user_id=user_id)
        await state.set_state(AdminStates.waiting_for_xp_amount)
        await callback.message.edit_text(f"Выбран пользователь {user_id}.\nТекущий XP: {user.xp} ✨.\nОтправьте новое количество XP:", reply_markup=get_back_button("admin_main"))
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    users = await db.get_all_users()
    sent = 0
    for u in users:
        try:
            if message.photo:
                await message.copy_to(u.id)
            else:
                await message.copy_to(u.id)
            sent += 1
        except Exception:
            pass
    await message.answer(f"Рассылка отправлена {sent} пользователям.", reply_markup=get_back_button("admin_main"))
    await state.clear()

@router.message(F.text.startswith("/ban "))
async def cmd_ban(message: Message, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        user_id = int(message.text.split()[1])
        user = await db.get_user(user_id)
        user.is_banned = True
        await db.update_user(user)
        await message.answer(f"Пользователь {user_id} забанен.")
    except Exception as e:
        await message.answer("Ошибка: /ban <user_id>")

@router.message(F.text.startswith("/unban "))
async def cmd_unban(message: Message, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        user_id = int(message.text.split()[1])
        user = await db.get_user(user_id)
        user.is_banned = False
        await db.update_user(user)
        await message.answer(f"Пользователь {user_id} разбанен.")
    except Exception as e:
        await message.answer("Ошибка: /unban <user_id>")

@router.message(F.text == "/maintenance")
async def cmd_maintenance(message: Message, db: Database):
    if not is_admin(message.from_user.id): return
    
    # Toggle maintenance mode
    async with db._conn.execute("SELECT value FROM settings WHERE key = 'maintenance'") as cursor:
        row = await cursor.fetchone()
        
    current_state = row[0] if row else "false"
    new_state = "false" if current_state == "true" else "true"
    
    await db._conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('maintenance', ?)", (new_state,))
    await db._conn.commit()
    
    state_str = "ВКЛЮЧЕН" if new_state == "true" else "ВЫКЛЮЧЕН"
    await message.answer(f"Режим обслуживания (Maintenance) {state_str}.")

@router.message(F.text == "/system")
async def cmd_system(message: Message):
    if not is_admin(message.from_user.id): return
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    text = f"💻 <b>Система</b>\nCPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%\nOS: {platform.system()}"
    await message.answer(text)

@router.message(F.text.startswith("/addpromo "))
async def cmd_addpromo(message: Message, db: Database):
    if not is_admin(message.from_user.id): return
    # /addpromo CODE COINS XP MAX_USES
    parts = message.text.split()
    if len(parts) != 5:
        await message.answer("Формат: <code>/addpromo CODE COINS XP MAX_USES</code>\nПример: <code>/addpromo MAHIRO 1000 50 10</code>")
        return
        
    code, coins, xp, max_uses = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
    await db._conn.execute('INSERT OR REPLACE INTO promocodes (code, reward_coins, reward_xp, max_uses, current_uses) VALUES (?, ?, ?, ?, 0)', (code, coins, xp, max_uses))
    await db._conn.commit()
    await message.answer(f"✅ Промокод <code>{html_decoration.quote(code)}</code> создан! Дает: {coins} 🪙, {xp} XP. Использований: {max_uses}")

@router.message(F.text == "/logs")
async def cmd_logs(message: Message):
    if not is_admin(message.from_user.id): return
    if os.path.exists("logs/mahiro.log"):
        await message.answer_document(FSInputFile("logs/mahiro.log"))
    else:
        await message.answer("Файл логов не найден.")

@router.message(F.text == "/reload_config")
@router.callback_query(F.data == "admin_reload")
async def admin_reload(event):
    user_id = event.from_user.id
    if not is_admin(user_id): return
    global settings
    settings = get_settings()
    if isinstance(event, Message):
        await event.answer("Конфиг успешно перезагружен из .env!")
    else:
        await event.message.edit_text("Конфиг успешно перезагружен из .env!", reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_diag")
async def admin_diag(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    text = f"🔧 <b>Диагностика</b>\nПуть к БД: {db.db_path}\nВсего пользователей: {len(users)}\nСтатус: Онлайн"
    await callback.message.edit_text(text, reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_whitelist_menu")
async def admin_whitelist_menu(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    enable_wl = await db.get_setting("enable_whitelist", str(settings.ENABLE_WHITELIST).lower()) == "true"
    status = "Вкл" if enable_wl else "Выкл"
    wl = await db.get_whitelist()
    count = len(wl)
    await callback.message.edit_text("🔐 УПРАВЛЕНИЕ WHITELIST", reply_markup=get_whitelist_menu(status, count))

@router.callback_query(F.data == "admin_blacklist_menu")
async def admin_blacklist_menu(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    banned_users = [u for u in users if u.is_banned]
    count = len(banned_users)
    await callback.message.edit_text("🚫 УПРАВЛЕНИЕ BLACKLIST", reply_markup=get_blacklist_menu(count))

@router.callback_query(F.data == "admin_toggle_whitelist")
async def admin_toggle_whitelist(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    enable_wl = await db.get_setting("enable_whitelist", str(settings.ENABLE_WHITELIST).lower()) == "true"
    new_status = "false" if enable_wl else "true"
    await db.set_setting("enable_whitelist", new_status)
    status = "Вкл" if new_status == "true" else "Выкл"
    wl = await db.get_whitelist()
    count = len(wl)
    await callback.message.edit_text("🔐 УПРАВЛЕНИЕ WHITELIST", reply_markup=get_whitelist_menu(status, count))

@router.callback_query(F.data == "admin_list_whitelist")
async def admin_list_whitelist(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    wl = await db.get_whitelist()
    text = f"📋 WHITELIST ({len(wl)})\n\n" + "\n".join(str(i) for i in wl)
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_whitelist_menu"))

@router.callback_query(F.data == "admin_list_blacklist")
async def admin_list_blacklist(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    banned_users = [u.id for u in users if u.is_banned]
    text = f"🚫 BLACKLIST ({len(banned_users)})\n\n" + "\n".join(str(i) for i in banned_users)
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_blacklist_menu"))

@router.callback_query(F.data == "admin_whitelist_add")
async def admin_whitelist_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_whitelist)
    await callback.message.edit_text("Отправьте ID пользователя, чтобы добавить его в белый список:", reply_markup=get_back_button("admin_whitelist_menu"))

@router.message(AdminStates.waiting_for_whitelist)
async def process_whitelist(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text)
        await db.add_to_whitelist(uid)
        await message.answer(f"Пользователь {uid} добавлен в белый список.", reply_markup=get_back_button("admin_whitelist_menu"))
    except Exception:
        await message.answer("Неверный ID пользователя.", reply_markup=get_back_button("admin_whitelist_menu"))
    await state.clear()

@router.callback_query(F.data == "admin_whitelist_remove")
async def admin_whitelist_remove(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_blacklist)
    await callback.message.edit_text("Чтобы удалить юзера из вайтлиста, забаньте его через Blacklist меню или через команду /ban.", reply_markup=get_back_button("admin_whitelist_menu"))

@router.callback_query(F.data == "admin_blacklist_add")
async def admin_blacklist_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_blacklist)
    await callback.message.edit_text("Отправьте ID пользователя, чтобы добавить его в черный список:", reply_markup=get_back_button("admin_blacklist_menu"))

@router.message(AdminStates.waiting_for_blacklist)
async def process_blacklist(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text)
        user = await db.get_user(uid)
        user.is_banned = True
        await db.update_user(user)
        await message.answer(f"Пользователь {uid} забанен.", reply_markup=get_back_button("admin_blacklist_menu"))
    except Exception:
        await message.answer("Неверный ID пользователя.", reply_markup=get_back_button("admin_blacklist_menu"))
    await state.clear()

@router.callback_query(F.data == "admin_blacklist_remove")
async def admin_blacklist_remove(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_unblacklist)
    await callback.message.edit_text("Отправьте ID пользователя, чтобы разбанить его:", reply_markup=get_back_button("admin_blacklist_menu"))

@router.message(AdminStates.waiting_for_unblacklist)
async def process_unblacklist(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text)
        user = await db.get_user(uid)
        user.is_banned = False
        await db.update_user(user)
        await message.answer(f"Пользователь {uid} успешно разбанен.", reply_markup=get_back_button("admin_blacklist_menu"))
    except Exception:
        await message.answer("Неверный ID пользователя.", reply_markup=get_back_button("admin_blacklist_menu"))
    await state.clear()

@router.callback_query(F.data == "admin_market")
async def admin_market(callback: CallbackQuery, db: Database):
    await admin_market_page(callback, db, 0)

@router.callback_query(F.data.startswith("admin_market_page_"))
async def admin_market_page_cb(callback: CallbackQuery, db: Database):
    page = int(callback.data.split("_")[-1])
    await admin_market_page(callback, db, page)

async def admin_market_page(callback: CallbackQuery, db: Database, page: int):
    if not is_admin(callback.from_user.id): return
    
    async with db._conn.execute('SELECT m.id, m.seller_id, m.item_type, m.item_id, m.price FROM market_lots m ORDER BY m.id DESC') as cursor:
        lots = await cursor.fetchall()
        
    if not lots:
        await callback.message.edit_text("🛒 Рынок пуст.", reply_markup=get_back_button("admin_main"))
        return
        
    items_per_page = 5
    total_pages = (len(lots) - 1) // items_per_page + 1
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * items_per_page
    page_lots = lots[start_idx:start_idx+items_per_page]
    
    text = f"🛒 <b>Управление Рынком</b> (Стр. {page+1}/{total_pages})\n\n"
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = []
    
    for lot in page_lots:
        l_id, s_id, i_type, i_id, price = lot
        text += f"Лот #{l_id} | Продавец: {s_id} | Тип: {i_type} | ID Предмета: {i_id} | Цена: {price} 🪙\n"
        kb.append([InlineKeyboardButton(text=f"🗑️ Удалить Лот #{l_id}", callback_data=f"admin_market_del_{l_id}")])
        
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_market_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_market_page_{page+1}"))
    if nav: kb.append(nav)
    
    kb.append([InlineKeyboardButton(text="🧹 Очистить весь рынок", callback_data="admin_market_clear")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("admin_market_del_"))
async def admin_market_del(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    lot_id = int(callback.data.split("_")[-1])
    
    await db._conn.execute('DELETE FROM market_lots WHERE id = ?', (lot_id,))
    await db._conn.commit()
    await callback.answer(f"Лот #{lot_id} удален.", show_alert=True)
    await admin_market_page(callback, db, 0)

@router.callback_query(F.data == "admin_market_clear")
async def admin_market_clear(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    await db._conn.execute('DELETE FROM market_lots')
    await db._conn.commit()
    await callback.answer("Рынок полностью очищен!", show_alert=True)
    await callback.message.edit_text("Рынок очищен.", reply_markup=get_back_button("admin_main"))
