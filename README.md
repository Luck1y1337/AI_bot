<div align="center">
  <img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjRtdHczMXQxeGRuYzhxaHJhOGc1aGxhdDhpOHYxd3lndjJrczBqMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LAKIIRqtM1dqE/giphy.gif" width="200" alt="Mahiro">

  # Mahiro Bot

  **Telegram-бот с ИИ-персонажем, игровой экономикой и социальными механиками**

  [![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://python.org)
  [![Aiogram 3](https://img.shields.io/badge/Aiogram-3.x-blueviolet)](https://aiogram.dev/)
  [![Mistral AI](https://img.shields.io/badge/Mistral_AI-Pixtral-ff6f00)](https://mistral.ai/)
  [![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003b57)](https://www.sqlite.org/)
</div>

---

## О проекте

Ролевой бот от лица **Махиро Ояма** из аниме *"Onimai: I'm Now Your Sister!"*. Бот обладает собственным настроением, памятью, системой доверия и проработанной экономикой с PvP-элементами.

**Ключевые особенности:**
- Диалоги через Mistral AI с контекстом и памятью
- Анализ изображений (Pixtral Vision)
- Полная экономическая система (валюта, бизнесы, банк, криптобиржа)
- PvP-игры (казино, камень-ножницы-бумага, рулетка)
- Кланы с войнами и рейд-боссами
- Гача-система с карточками и глобальным рынком
- Браки, питомцы (тамагочи), подземелья
- Админ-панель с аналитикой и веб-дашбордом

---

## Быстрый старт

### Требования
- Python 3.11+
- Токен Telegram бота ([@BotFather](https://t.me/BotFather))
- API-ключ [Mistral AI](https://mistral.ai/)

### Установка

```bash
git clone https://github.com/YOUR_USERNAME/mahiro-bot.git
cd mahiro-bot
pip install -r requirements.txt
```

### Настройка

```bash
cp .env.example .env
```

Заполните `.env`:
```env
TELEGRAM_TOKEN=ваш_токен
MISTRAL_API_KEY=ваш_ключ
ADMIN_USER_IDS=123456789
ADMIN_PANEL_TOKEN=секретный_токен
ENABLE_WHITELIST=false
```

### Запуск

```bash
python main.py
```

При первом запуске автоматически создастся БД и необходимые папки.

### Docker

```bash
docker-compose up -d
```

---

## Структура проекта

```
mahiro_bot/
├── main.py              # Точка входа
├── config/              # Настройки (.env)
├── database/            # Модели и Repository (SQLite)
├── ai/                  # Mistral API клиент, промпты
├── memory/              # Краткосрочная и долгосрочная память
├── bot/
│   ├── handlers/        # 25 обработчиков команд
│   ├── keyboards/       # Клавиатуры (Reply + Inline)
│   ├── middlewares/      # Антиспам, вайтлист, логирование
│   └── fsm/             # Состояния FSM
├── media/               # TTS, графики, изображения
├── utils/               # Достижения, форматирование, квесты
└── web/                 # Веб-дашборд (FastAPI)
```

---

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Начать диалог и пройти туториал |
| `/stats` | Профиль: коины, XP, достижения |
| `/mood` | Текущее настроение и доверие |
| `/voice` | Озвучка текста голосом |
| `/quiz` | Аниме-викторина |
| `/remind` | Установить напоминание |
| `/support` | Написать в поддержку |
| `/donate` | Пополнить баланс (Telegram Stars) |
| `/promo` | Активировать промокод |
| `/admin` | Админ-панель |

Основной функционал доступен через **Inline-кнопки** в меню бота.

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Бот-фреймворк | aiogram 3.x |
| ИИ | Mistral AI (mistral-small + pixtral-12b) |
| База данных | SQLite (aiosqlite, WAL) |
| Веб-панель | FastAPI + Jinja2 |
| Планировщик | APScheduler |
| Изображения | Pillow, matplotlib |
| TTS | gTTS |
| Деплой | Docker, Railway |

---

## Лицензия

MIT
