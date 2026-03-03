# 🍱 CaloTracko — Calorie Tracking Telegram Bot

A personal Telegram bot that estimates calories from food descriptions or photos using AI, tracks your daily and weekly intake, and helps you stay on top of your nutrition goals.

## ✨ Features

- 📸 **Log meals by photo or text** — AI estimates calories and macros instantly
- 📊 **Daily & weekly summaries** — track progress against your calorie goal
- 💾 **Save favourite meals** — log recurring meals with one tap
- 👤 **Personalised profile** — age, height, weight, activity level, and goal weight
- 🎯 **Smart calorie goal** — calculated via Mifflin-St Jeor equation
- 🔔 **Meal reminders** — configurable daily nudge if no meals logged
- 🔐 **Authorised users only** — restrict access to specific Telegram IDs

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot framework | `python-telegram-bot` v20 |
| Web server | FastAPI + Mangum |
| Hosting | Vercel (serverless) |
| Database | Supabase (PostgreSQL via `asyncpg`) |
| AI | OpenAI-compatible API (vision + text) |

## 🚀 Self-Hosting Guide

### Prerequisites
- Python 3.11+
- A [Telegram bot token](https://t.me/BotFather)
- An [OpenAI-compatible API key](https://platform.openai.com)
- A [Supabase](https://supabase.com) project
- A [Vercel](https://vercel.com) account

### 1. Clone & install
```bash
git clone https://github.com/your-username/calotracko.git
cd calotracko
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Fill in your values in .env
```

### 3. Set up Supabase
1. Create a new Supabase project
2. Open **SQL Editor** and run `schema.sql`
3. Copy the **Transaction pooler** connection string (port `6543`) into `DATABASE_URL`

### 4. Run locally (polling mode)
```bash
python main.py
```

### 5. Deploy to Vercel
```bash
vercel --prod
```
Then register the webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-app.vercel.app/webhook"
```

## 📁 Project Structure

```
├── api/
│   └── index.py          # FastAPI webhook entry point (Vercel)
├── handlers/
│   ├── log_meal.py       # Meal logging flow
│   ├── profile.py        # User profile setup
│   ├── tracking.py       # Daily/weekly/history summaries
│   ├── saved_meals.py    # Saved meal management
│   ├── reminder.py       # Reminder settings
│   └── goal.py           # Calorie goal management
├── main.py               # Bot setup and polling (local dev)
├── database.py           # Supabase database layer
├── ai_service.py         # AI calorie estimation
├── config.py             # Environment variable loader
├── schema.sql            # Supabase table definitions
├── vercel.json           # Vercel deployment config
└── .env.example          # Environment variable template
```

## 🔒 Security

- Bot restricted to authorised Telegram user IDs via `AUTHORIZED_TELEGRAM_IDS`
- AI prompt injection defences in `ai_service.py`
- All secrets managed via environment variables (never committed)

## 📄 License

MIT
