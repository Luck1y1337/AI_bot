<div align="center">
  <img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjRtdHczMXQxeGRuYzhxaHJhOGc1aGxhdDhpOHYxd3lndjJrczBqMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LAKIIRqtM1dqE/giphy.gif" width="300" alt="Mahiro GIF">
  
  # 🌸 Mahiro Telegram Bot (Махиро) 🌸
  
  **Умный, ролевой Telegram-бот на базе Mistral AI (Pixtral-12B) с уникальной экономикой и Web-Дашбордом.**
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blueviolet?style=for-the-badge)](https://aiogram.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Mistral AI](https://img.shields.io/badge/Mistral%20AI-Pixtral-orange?style=for-the-badge)](https://mistral.ai/)
  [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 📖 О Проекте

Инновационный Telegram-бот от лица Махиро Ояма (Mahiro Oyama) из аниме *"Onimai: I'm Now Your Sister!"*. 
Это не просто бот-помощник, это полноценный виртуальный собеседник со своим характером, настроением, памятью и экономикой. Он умеет распознавать фотографии, генерировать голосовые ответы и даже запоминать ваши интересы!

<details>
<summary><b>✨ Нажмите, чтобы увидеть полный список возможностей (Features)</b></summary>

| Функция | Описание |
| :--- | :--- |
| **🧠 Продвинутый AI & Память** | Использование нейросети для ролевого общения. Бот имеет краткосрочную (контекст диалога) и долгосрочную (интересы, факты о вас) память. |
| **👀 Зрение (Vision)** | Вы можете отправлять боту фотографии, и он проанализирует их и отреагирует в образе Махиро! |
| **🎤 Голос (TTS)** | Генерация реалистичных голосовых ответов прямо в Telegram. |
| **💰 Экономика & Подарки** | Система `MahiroCoins` 🪙 и опыта (`XP` ✨). Вы можете дарить боту подарки, повышая его настроение и уровень доверия к вам. |
| **👑 Админ-Панель** | Мощная встроенная система управления: настройка баланса пользователей, просмотр статистики, аналитика, бан-листы и рассылка. |
| **🌐 Web Dashboard** | Полноценная веб-панель на FastAPI для мониторинга активности и изменения настроек нейросети "на лету". |
| **🛡 Служба Поддержки** | Встроенная тикет-система. Пользователи могут обратиться в поддержку, а администратор — ответить прямо через бота. |
| **💸 Telegram Stars** | Интеграция официальных платежей Telegram для покупки внутриигровой валюты. |

</details>

---

## 🚀 Быстрый Старт

> [!IMPORTANT]
> Для работы бота вам понадобятся API ключи от **Telegram** (BotFather) и **Mistral AI**.

### 1. Подготовка
Клонируйте репозиторий и перейдите в папку проекта:
```bash
git clone https://github.com/YOUR_USERNAME/mahiro-bot.git
cd mahiro-bot
```

### 2. Установка зависимостей
Убедитесь, что у вас установлен Python версии 3.10 или выше.
```bash
pip install -r requirements.txt
```

### 3. Настройка окружения
Скопируйте файл конфигурации:
```bash
cp .env.example .env
```
Откройте файл `.env` и заполните данные:
- `BOT_TOKEN` — ваш токен от BotFather.
- `MISTRAL_API_KEY` — ключ от платформы Mistral.
- `ADMIN_IDS` — ваш Telegram ID.

### 4. Запуск
```bash
python main.py
```
Бот мгновенно создаст локальную базу данных SQLite и будет готов к общению! 
🌐 Web-панель будет доступна по адресу `http://localhost:8000`.

---

## 📂 Архитектура Проекта

Проект спроектирован с учетом масштабируемости и чистоты кода:

```text
mahiro_bot/
├── ai/             # Интеграция с Mistral, система промптов и "Триггеры" ⚡
├── bot/            # Хендлеры Aiogram, FSM стейты, клавиатуры и мидлвари
├── database/       # ORM модели и репозиторий на основе aiosqlite
├── media/          # Работа с TTS (голос) и генерация графиков аналитики
├── memory/         # Логика долгосрочной и краткосрочной памяти ИИ
├── utils/          # Вспомогательные скрипты (антиспам, система достижений)
├── web/            # FastAPI приложение и маршруты для Web Dashboard
├── data/           # (Авто-создается) Локальная база данных .db
├── logs/           # (Авто-создается) Логи работы бота
└── main.py         # Точка входа приложения
```

---

## 🛠 Технологический Стек

- **Язык:** Python 3.10+
- **Telegram API Framework:** `aiogram 3.x`
- **Web/API Framework:** `FastAPI`, `Uvicorn`
- **База данных:** `aiosqlite`
- **Нейросеть:** `mistralai`
- **Дополнительно:** `psutil` (мониторинг системы), `matplotlib` (графики).

---

## 🤝 Вклад в проект

Мы всегда рады новым идеям! Если вы хотите улучшить бота:
1. Форкните репозиторий
2. Создайте свою ветку (`git checkout -b feature/AmazingFeature`)
3. Сделайте коммит (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте изменения (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📜 Лицензия
Проект распространяется по лицензии **MIT**. Используйте, модифицируйте и обучайтесь с удовольствием! 🍀
