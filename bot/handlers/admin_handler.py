from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from database.repository import Database
from config.settings import get_settings
from bot.fsm.states import AdminStates
from bot.keyboards.admin_kb import get_admin_main_kb
from media.charts import generate_activity_chart, generate_trust_chart
import psutil
import platform
import os
import zipfile
import csv
import json

router = Router()
settings = get_settings()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_USER_IDS

@router.message(F.text.in_(["/admin", "👑 Админ Панель"]))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ Панель", reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    users = await db.get_all_users()
    total_msgs = sum(u.message_count for u in users)
    text = f"📊 **Статистика**\nПользователей: {len(users)}\nСообщений: {total_msgs}"
    await callback.message.edit_text(text, reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_analytics")
async def admin_analytics(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id): return
    # Generate charts
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
    text = f"💻 **Система**\nCPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%\nOS: {platform.system()}"
    await callback.message.edit_text(text, reply_markup=get_admin_main_kb())

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
    await callback.message.edit_text("Отправьте сообщение для рассылки всем пользователям:")

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
        except:
            pass
    await message.answer(f"Рассылка отправлена {sent} пользователям.")
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
    text = f"💻 **Система**\nCPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%\nOS: {platform.system()}"
    await message.answer(text)

@router.message(F.text.startswith("/addpromo "))
async def cmd_addpromo(message: Message, db: Database):
    if not is_admin(message.from_user.id): return
    # /addpromo CODE COINS XP MAX_USES
    parts = message.text.split()
    if len(parts) != 5:
        await message.answer("Формат: `/addpromo CODE COINS XP MAX_USES`\nПример: `/addpromo MAHIRO 1000 50 10`")
        return
        
    code, coins, xp, max_uses = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
    await db._conn.execute('INSERT OR REPLACE INTO promocodes (code, reward_coins, reward_xp, max_uses, current_uses) VALUES (?, ?, ?, ?, 0)', (code, coins, xp, max_uses))
    await db._conn.commit()
    await message.answer(f"✅ Промокод `{code}` создан! Дает: {coins} 🪙, {xp} XP. Использований: {max_uses}")

@router.message(F.text.startswith("/promo "))
async def cmd_promo(message: Message, db: Database):
    code = message.text.split(" ", 1)[1].strip()
    
    async with db._conn.execute('SELECT reward_coins, reward_xp, max_uses, current_uses FROM promocodes WHERE code = ?', (code,)) as cursor:
        row = await cursor.fetchone()
        
    if not row:
        await message.answer("Этот промокод не существует или введен неверно.")
        return
        
    coins, xp, max_uses, current_uses = row
    if current_uses >= max_uses:
        await message.answer("Этот промокод уже закончился! :(")
        return
        
    # Give reward
    user = await db.get_user(message.from_user.id)
    user.coins += coins
    user.xp += xp
    await db.update_user(user)
    
    # Increment uses
    await db._conn.execute('UPDATE promocodes SET current_uses = current_uses + 1 WHERE code = ?', (code,))
    await db._conn.commit()
    
    await message.answer(f"🎉 Промокод активирован! Ты получил {coins} 🪙 и {xp} XP.")

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
    text = f"🔧 **Диагностика**\nПуть к БД: {db.db_path}\nВсего пользователей: {len(users)}\nСтатус: Онлайн"
    await callback.message.edit_text(text, reply_markup=get_admin_main_kb())

@router.callback_query(F.data == "admin_whitelist")
async def admin_whitelist(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_whitelist)
    await callback.message.edit_text("Отправьте ID пользователя, чтобы добавить его в белый список:")

@router.message(AdminStates.waiting_for_whitelist)
async def process_whitelist(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text)
        if uid not in settings.WHITELIST_USER_IDS:
            settings.WHITELIST_USER_IDS.append(uid)
        await message.answer(f"Пользователь {uid} добавлен в белый список.")
    except:
        await message.answer("Неверный ID пользователя.")
    await state.clear()

@router.callback_query(F.data == "admin_blacklist")
async def admin_blacklist(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_blacklist)
    await callback.message.edit_text("Отправьте ID пользователя, чтобы добавить его в черный список:")

@router.message(AdminStates.waiting_for_blacklist)
async def process_blacklist(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text)
        if uid not in settings.BLACKLIST_USER_IDS:
            settings.BLACKLIST_USER_IDS.append(uid)
        await message.answer(f"Пользователь {uid} добавлен в черный список.")
    except:
        await message.answer("Неверный ID пользователя.")
    await state.clear()
