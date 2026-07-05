<div align="center">

# 🌸 Mahiro Bot

### AI-компаньон в Telegram с ролевыми диалогами, экономикой, PvP-играми и кланами

[![CI](https://github.com/Luck1y1337/AI_bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Luck1y1337/AI_bot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-7B68EE?style=flat-square)](https://aiogram.dev/)
[![Mistral AI](https://img.shields.io/badge/Mistral_AI-ff6f00?style=flat-square)](https://mistral.ai/)
[![SQLite](https://img.shields.io/badge/SQLite-003b57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](#-деплой)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

**~8 000 строк** · **60 модулей** · **26 хендлеров** · **25+ таблиц БД**

</div>

---

## 📖 О проекте

**Mahiro Bot** — асинхронный Telegram-бот на **aiogram 3**, в котором ИИ-персонаж
(Махиро Ояма из аниме *Onimai: I'm Now Your Sister!*) объединён с полноценной
игровой вселенной: экономикой, PvP- и PvE-играми, кланами, питомцами, крафтом и
социальными механиками.

Диалоги ведёт **Mistral AI**: у персонажа есть настроение, уровень доверия и
двухуровневая память о собеседнике. Вся навигация — через **inline-кнопки**,
данные хранятся в **SQLite** (WAL), фоновые задачи крутит **APScheduler**.

> Проект построен по слоистой архитектуре (config → database → handlers →
> keyboards → middlewares), с параметризованными SQL-запросами, экранированием
> пользовательского ввода и защитой админ-функций на уровне роутеров.

---

## ✨ Ключевые возможности

### 🧠 Искусственный интеллект
| Функция | Описание |
|---------|----------|
| Ролевые диалоги | Ответы «в характере»; тон зависит от уровня доверия |
| Двухуровневая память | Краткосрочный контекст диалога + долгосрочные факты о пользователе |
| Система доверия | 0–100 %, влияет на реплики и поведение |
| Динамическое настроение | 7 состояний (happy, sad, annoyed, excited, tired, sleepy, normal) |
| Анализ фото | Комментирование изображений через Pixtral Vision |
| Голос | TTS-озвучка ответов (gTTS + ffmpeg) |
| Кастомная роль | VIP могут задать боту собственный системный промпт |

### 💰 Экономика
`MahiroCoins (🪙)` — валюта · `XP (✨)` — опыт за активность

Ежедневный бонус · пассивный доход с бизнесов · банк (вклады и кредиты) ·
почасовая криптобиржа · ежедневные контракты · магазин баффов и титулов ·
P2P-переводы с налогом · донаты через **Telegram Stars**.

### 🎮 Игры
| Игра | Тип | Механика |
|------|-----|----------|
| Coinflip | PvP | Ставка 50/50 против другого игрока |
| Камень-Ножницы-Бумага | PvP | Лобби на 500 / 2000 🪙 |
| Рулетка | PvP | Русская рулетка на коины |
| Гача | PvE | Карточки 4 редкостей (Common → Legendary) |
| Подземелья | PvE | Экспедиции, шанс зависит от крафта |
| Рейд на босса | Co-op | Общий HP, атака раз в час |
| Викторина | Solo | Аниме-квиз за XP и коины |
| Игры с ИИ | Solo | «Угадай число» и словесные игры с Mistral |

### 🐾 Питомцы · 🏰 Кланы · 🤝 Социальное · ⚒️ Крафт
- **Тамагочи:** слайм эволюционирует (Ур. 1 → 10 → 20), сытый даёт бонус к урону в рейдах.
- **Кланы:** казна, 24-часовые войны, клановые боссы, топ по XP.
- **Социальное:** браки и совместный дом, репутация (+rep), награды за голову (bounty), трейд, глобальный и чёрный рынок.
- **Крафт:** добыча ресурсов → меч / броня / кольцо → преимущество в подземельях.

### 👑 Админ-панель (из Telegram)
Модерация (бан / вайтлист / блэклист) · выдача коинов и XP · промокоды ·
рассылка · управление рынком · мониторинг CPU/RAM/Disk · экспорт данных
(CSV/JSON/ZIP) · maintenance-режим · reload `.env` без рестарта.

---

## 🔒 Безопасность

- **Секреты только через окружение** — `.env` в `.gitignore`, в репозитории лишь `.env.example`.
- **Параметризованные SQL-запросы** — без конкатенации, устойчивость к инъекциям.
- **Экранирование ввода** (`html.quote`) для всего пользовательского текста, попадающего в HTML-разметку (имена кланов, тикеты, история диалога, ответы ИИ).
- **Бан на уровне middleware** — проверка применяется и к сообщениям, и к inline-кнопкам; UI-«сокрытие» не заменяет проверку прав.
- **Защита админ-функций** — все хендлеры проверяют `ADMIN_USER_IDS`.
- **Rate limiting** — антифлуд-middleware (кулдаун + мут при спаме).

---

## 🛠️ Технологический стек

| Слой | Технология |
|------|-----------|
| Фреймворк | **aiogram 3.x** (async Telegram Bot API) |
| ИИ | **Mistral Small** (текст) + **Pixtral 12B** (зрение) |
| База данных | **SQLite + aiosqlite** (WAL, индексы) |
| Планировщик | **APScheduler** (напоминания, крипта, бэкапы) |
| Медиа | **Pillow** (карточки), **matplotlib** (графики), **gTTS + ffmpeg** (голос) |
| Конфигурация | **Pydantic** + **python-dotenv** |
| Деплой | **Docker / Railway** |

---

## 🏗️ Архитектура

```
mahiro_bot/
├── main.py                # Точка входа, middleware, планировщик задач
├── config/settings.py     # Pydantic-валидация .env
├── ai/                    # Клиент Mistral, построение промпта, быстрые триггеры
├── database/              # models.py (dataclass) + repository.py (весь доступ к БД)
├── memory/                # Краткосрочная (RAM) и долгосрочная (JSON) память
├── bot/
│   ├── handlers/          # 26 модулей: старт, экономика, игры, кланы, админка …
│   ├── keyboards/         # Reply + Inline клавиатуры
│   ├── middlewares/       # Logging · Maintenance · Whitelist · AntiSpam
│   └── fsm/states.py      # FSM-состояния
├── media/ · utils/        # TTS, профили, графики, достижения, форматирование
├── Dockerfile · railway.json
└── requirements.txt · .env.example
```

**Поток обработки события** (message или callback):

```
Telegram → Dispatcher → Middleware Chain → Router → Handler
                            │                          │
              Logging → Maintenance →           ┌──────┴──────┐
              Whitelist → AntiSpam           Database     Mistral AI
                                             (SQLite)      (API)
                                                │            │
                                             Memory       Response
                                          (RAM + JSON)
```

---

## 🚀 Быстрый старт

**Требования:** Python 3.11+, токен от [@BotFather](https://t.me/BotFather),
ключ [Mistral AI](https://console.mistral.ai/), опционально `ffmpeg` (для голоса).

```bash
git clone https://github.com/Luck1y1337/AI_bot.git
cd AI_bot
pip install -r requirements.txt
cp .env.example .env      # затем заполните значения
python main.py
```

`.env`:

```env
TELEGRAM_TOKEN=токен_от_botfather
MISTRAL_API_KEY=ключ_mistral
ADMIN_USER_IDS=123456789
ENABLE_WHITELIST=false
```

> При первом запуске автоматически создаются папки `data/`, `cache/`, `logs/` и база данных.

### Переменные окружения

| Переменная | Обязательна | Описание |
|-----------|:-----------:|----------|
| `TELEGRAM_TOKEN` | ✅ | Токен бота от @BotFather |
| `MISTRAL_API_KEY` | ✅ | API-ключ Mistral AI |
| `ADMIN_USER_IDS` | ✅ | ID администраторов (через запятую) |
| `ENABLE_WHITELIST` | | Режим белого списка (`true`/`false`) |
| `WHITELIST_USER_IDS` | | Предодобренные ID |
| `BLACKLIST_USER_IDS` | | Заблокированные ID |
| `DB_PATH` | | Путь к SQLite-базе (по умолчанию `data/mahiro.db`; в Docker — `/data/mahiro.db`) |

---

## 🐳 Деплой

Сборка идёт по `Dockerfile` (см. `railway.json`), команда запуска — `python main.py`.

> ⚠️ **Персистентность БД.** Путь к базе задаётся переменной `DB_PATH`; в
> `Dockerfile` она уже выставлена в `/data/mahiro.db`. Чтобы данные (база и
> долгосрочная память) не терялись при передеплое, в Railway создайте **Volume**
> и примонтируйте его на `/data`. Больше ничего настраивать не нужно — переменную
> `DB_PATH` в дашборде добавлять необязательно, она приходит из образа.

> ⚠️ **Один инстанс.** Бот работает через long polling — нельзя одновременно держать
> локальный и хостинговый инстанс с одним `TELEGRAM_TOKEN` (Telegram вернёт `Conflict`).

---

## 📋 Команды

<details>
<summary><b>Пользовательские</b></summary>

| Команда | Описание |
|---------|----------|
| `/start` | Начать диалог и пройти туториал |
| `/stats` | Профиль: статистика и достижения |
| `/mood` | Настроение и уровень доверия |
| `/reset` | Сброс краткосрочной памяти ИИ |
| `/voice` | Озвучка текста голосом Махиро |
| `/quiz` | Аниме-викторина |
| `/remind` · `/reminders` | Напоминания |
| `/leaderboard` | Топ-10 по XP |
| `/gift` · `/donate` · `/promo` | Подарки, донаты, промокоды |
| `/support` | Тикет администратору |

</details>

<details>
<summary><b>Админские</b></summary>

| Команда | Описание |
|---------|----------|
| `/admin` | Открыть админ-панель |
| `/addpromo CODE 100 50 10` | Создать промокод (коины, XP, кол-во) |
| `/ban ID` · `/unban ID` | Блокировка / разблокировка |
| `/maintenance` | Режим обслуживания |
| `/system` | Нагрузка сервера (CPU / RAM / Disk) |
| `/logs` | Скачать логи |
| `/reload_config` | Перезагрузить `.env` без рестарта |

</details>

---

## 🗺️ Roadmap

- [x] Система уровней и титулов
- [x] Streak-бонусы за серию ежедневных входов
- [x] Реферальная система
- [x] Экранирование ввода и enforce-бан на уровне middleware
- [ ] Турниры с таблицей результатов
- [ ] Сезонный рейтинг с наградами
- [ ] Telegram Mini App (WebApp)

---

## 📄 Лицензия

Распространяется под лицензией [MIT](LICENSE).

<div align="center">
<sub>Сделано с ❤️ на Python и aiogram</sub>
</div>
