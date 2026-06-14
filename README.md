# Energy Chief ⚡🔥

Energy Chief is a Telegram bot companion for understanding energy consumption and helping users optimise their energy usage. It integrates with [Enode](https://developers.enode.com/) to read real-time smart meter data and notifies users about available energy in their Renewable Energy Community (CER — *Comunità Energetica Rinnovabile*).

---

## ✨ Features

| Feature | Status | Description |
|---|---|---|
| **Telegram Bot** | ✅ | Italian-language interface with conversation-based setup |
| **Enode Integration** | ✅ | OAuth2-based API client to read smart meters via Enode |
| **REC Monitoring** | ✅ | Periodic polling and webhook-based collection of meter readings |
| **Energy Availability Alerts** | ✅ | Automatic Telegram notifications when REC energy exceeds a threshold |
| **User Profile Setup** | ✅ | Configure heating system, electricity/gas rates, and REC membership |
| **Real-time Meter Data** | ✅ | View live consumption/production from linked smart meters |
| **Webhook Support** | ✅ | Event-driven updates from Enode (near-real-time) |
| **Dual Database** | ✅ | SQLite for local dev, PostgreSQL for production |
| **Alembic Migrations** | ✅ | Managed schema migrations |
| **Cost Comparison** | 🔄 Planned | Compare heat pump vs gas boiler convenience |

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.14+ |
| **Web Framework** | FastAPI |
| **Telegram Client** | python-telegram-bot (PTB) v22+ |
| **Enode API Client** | httpx (async HTTP) |
| **ORM / Database** | SQLAlchemy 2.0 |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **Migrations** | Alembic |
| **Server** | Uvicorn (ASGI) |
| **Package Manager** | uv |

---

## 📁 Directory Architecture

```
Energychief/
├── app.py                           # FastAPI entry point with lifespan management
├── serve.py                         # Production server runner (Uvicorn)
├── pyproject.toml                   # Project metadata and dependencies
├── alembic.ini                      # Alembic configuration
├── recs_data.csv                    # Seed data for Renewable Energy Communities
├── .env                             # Environment variables (not committed)
│
├── shared/                          # Core shared modules (no framework dependency)
│   ├── __init__.py
│   ├── config.py                    # Environment variables loader
│   ├── engine.py                    # SQLAlchemy engine & session factory
│   ├── models.py                    # ORM models (Rec, User, Meter, EnergyReading, WebhookEvent)
│   └── database.py                  # All database access functions
│
├── backend/                         # Backend logic (Enode integration, data collection)
│   ├── __init__.py
│   ├── enode_api.py                 # Enode HTTP client (OAuth, meters, webhook CRUD)
│   ├── enode_webhook_handler.py     # Enode webhook signature verification & event processing
│   ├── rec_monitor.py               # Periodic polling task to fetch all meters
│   └── manage_webhooks.py           # CLI tool for Enode webhook management
│
├── frontend/                        # Telegram bot frontend
│   ├── __init__.py
│   ├── telegram_app.py              # PTB Application factory + notification job
│   ├── messages.py                  # All user-facing Italian strings
│   ├── validators.py                # Input validation functions
│   └── handlers/
│       ├── __init__.py
│       ├── general.py               # /start, /help, /status commands
│       ├── setup.py                 # /setup conversation handler (multi-step)
│       └── enode.py                 # /collegacontatore, /energia commands
│
├── alembic/
│   ├── env.py                       # Alembic environment (reads DATABASE_URL from env)
│   ├── script.py.mako               # Migration template
│   └── versions/
│       └── bb84e8355ce8_initial_schema.py  # Initial schema migration
│
└── docs/
    └── Enode_webhook.md             # Enode webhook documentation reference
```

---

## 🔍 Module Breakdown

### `app.py` — FastAPI Entry Point

The main application orchestrator. Uses a lifespan context manager to:

1. **Startup**: Initialise the database (create tables), seed RECs from CSV, start the background Enode polling loop, build and start the Telegram bot (either webhook or polling mode).
2. **Shutdown**: Cancel the background polling task, stop the Telegram bot gracefully.

**Endpoints:**
| Route | Method | Description |
|---|---|---|
| `/health` | GET | Health check, returns `{"status": "ok"}` |
| `/webhooks/telegram` | POST | Receives Telegram updates (webhook mode) |
| `/webhooks/enode` | POST | Receives Enode real-time events |

The bot supports two modes:
- **Polling** (default): the bot polls Telegram servers for updates — no public URL needed.
- **Webhook**: set `WEBHOOK_BASE_URL` in `.env` to use a public URL (e.g. ngrok, production). Telegram and Enode updates are pushed to FastAPI endpoints.

### `serve.py` — Production Server

Starts Uvicorn on `127.0.0.1:8000`. Used by Uberspace supervisord in production.

### `shared/config.py` — Configuration

Loads `.env` via `python-dotenv` and exposes typed constants:
- `TELEGRAM_TOKEN`, `WEBHOOK_BASE_URL`, `ENODE_WEBHOOK_SECRET`
- `ENODE_API_URL`, `REDIRECT_URI`

### `shared/engine.py` — Database Engine

Creates the SQLAlchemy `engine` and `SessionLocal` from `DATABASE_URL`. Supports both SQLite (auto-creates the `db/` directory) and PostgreSQL.

### `shared/models.py` — ORM Models

Five tables defined as SQLAlchemy `DeclarativeBase` subclasses:

| Model | Table | Key Fields |
|---|---|---|
| **Rec** | `recs` | `rec_id`, `name` (unique), `latitude`, `longitude`, `pod_prefix` |
| **User** | `users` | `user_id` (PK), `telegram_id` (unique), `first_name`, `heating`, `electricity_rate`, `gas_rate`, `rec_id` (FK), `threshold_kwh`, `notification_interval_hours`, `last_notified_at` |
| **Meter** | `meters` | `meter_id` (PK), `owner_user_id` (FK), `producer`, `model`, `consumption_enabled`, `production_enabled` |
| **EnergyReading** | `energy_readings` | Compound PK (`meter_id`, `timestamp`), `power_kw` |
| **WebhookEvent** | `webhook_events` | `id`, `delivery_id`, `event_type`, `meter_id`, `payload`, `received_at` |

### `shared/database.py` — Database Access Layer

All database operations in one module. Key functions:

**Users:**
- `upsert_user_by_telegram(telegram_id, first_name, heating, electricity_rate, gas_rate, rec_id)` — Create or update a user
- `get_user_by_telegram_id(telegram_id)` — Find user by Telegram ID
- `get_user_by_user_id(user_id)` — Find user by internal PK
- `update_last_notified(telegram_id)` — Update notification timestamp

**RECs:**
- `seed_recs_from_csv(csv_path)` — Seed RECs from `recs_data.csv`
- `get_all_recs()` — List all RECs
- `get_users_in_rec(rec_id)` — Get all users belonging to a REC
- `get_meters_for_rec(rec_id)` — Get meter IDs for all users in a REC

**Meters & Readings:**
- `upsert_meter(meter_id, owner_user_id, producer, model)` — Create or update a meter
- `save_energy_reading(meter_id, timestamp, power_kw)` — Store a reading (upsert by compound key)
- `get_latest_power_per_meter(rec_id)` — Latest reading per meter for a REC

**Webhook Logging:**
- `log_webhook_event(delivery_id, event_type, meter_id, payload)` — Persist incoming webhook events

### `backend/enode_api.py` — Enode API Client

Async HTTP client for the [Enode API](https://developers.enode.com/api/reference). Handles OAuth2 client credentials flow with automatic token refresh. Functions:

**Authentication:**
- `get_access_token()` — Returns a valid OAuth2 token (cached with 60s buffer)

**Users & Meters:**
- `create_link_session(user_id)` — Returns a link URL the user opens to connect their meter (scopes: `meter:read:data`, language: `it-IT`)
- `get_meter(meter_id)` — Full meter object including `energyState`
- `get_user_meters(user_id)` — Meters for a specific Enode user
- `get_all_meters()` — All meters across all users (paginated, up to 50 per page)

**Webhook Management:**
- `list_webhooks()` — List all registered webhooks
- `create_webhook(url, secret, events)` — Register a new webhook subscription
- `get_webhook(webhook_id)`, `update_webhook(...)`, `delete_webhook(webhook_id)`, `test_webhook(webhook_id)` — CRUD operations

### `backend/enode_webhook_handler.py` — Webhook Processing

- `verify_enode_signature(payload, signature_header)` — HMAC-SHA1 verification using `ENODE_WEBHOOK_SECRET`
- `process_enode_event(event, delivery_id)` — Processes known event types (`user:meter:updated`, `user:meter:discovered`, `user:meter:deleted`, `enode:webhook:test`), upserts meter records, saves readings, and logs raw payloads

### `backend/rec_monitor.py` — Polling Task

- `collect_and_store_readings()` — Fetches all meters via `get_all_meters()`, saves the latest `energyState` for reachable meters. Runs every **60 minutes** (or 24h if webhooks are configured, as a safety-net backfill).

### `backend/manage_webhooks.py` — CLI Tool

A command-line utility for Enode webhook management:

```bash
# List all webhooks
uv run python -m backend.manage_webhooks list

# Create a webhook (auto-generates secret if not provided)
uv run python -m backend.manage_webhooks create

# Create with explicit URL and secret
uv run python -m backend.manage_webhooks create \
    --url https://example.com/webhooks/enode \
    --secret my-secret-123

# Show webhook details
uv run python -m backend.manage_webhooks show <webhook_id>

# Delete a webhook
uv run python -m backend.manage_webhooks delete <webhook_id>

# Send a test event
uv run python -m backend.manage_webhooks test <webhook_id>
```

### `frontend/telegram_app.py` — Telegram Bot Factory

Builds a `telegram.ext.Application` with:

**Commands:**
| Command | Handler | Description |
|---|---|---|
| `/start` | `general.start` | Welcome message |
| `/help` | `general.help_command` | List available commands |
| `/status` | `general.status` | Show current configuration |
| `/setup` | `setup.setup_start` | Multi-step profile configuration |
| `/collegacontatore` | `enode.handle_link_meter` | Get Enode link to connect a smart meter |
| `/energia` | `enode.handle_energy` | Show real-time energy consumption/production |
| `/cancel` | `setup.setup_cancel` | Cancel ongoing setup |

**Background Job:**
- `check_recs_and_notify(context)` — Every 60 minutes, checks if the total power in each REC exceeds the user's threshold. If so, sends a Telegram notification (only between 07:00–22:00, respecting per-user notification intervals).

### `frontend/messages.py` — UI Strings

All Italian user-facing messages in one file for easy customisation.

### `frontend/validators.py` — Input Validation

- `parse_positive_float(text)` — Parses a positive float, accepts both `.` and `,` as decimal separator

### `frontend/handlers/general.py` — Basic Commands

- `start()` — Welcome with bot name
- `help_command()` — Lists all commands
- `status()` — Shows user's saved profile from database

### `frontend/handlers/setup.py` — Setup Conversation

A 4-step `ConversationHandler`:
1. **Heating type** (`ASK_HEATING`): Choose from keyboard — *Heat pump*, *Gas boiler*, *Both*
2. **Electricity rate** (`ASK_ELECTRICITY_RATE`): Enter €/kWh
3. **Gas rate** (`ASK_GAS_RATE`): Enter €/Sm³
4. **REC selection** (`ASK_REC`): Choose by number or name from the seeded list

On completion, calls `upsert_user_by_telegram()` to persist the profile.

### `frontend/handlers/enode.py` — Enode Meter Commands

- `handle_link_meter()` — Creates an Enode link session and sends the URL to the user
- `handle_energy()` — Fetches all linked meters from Enode, displays consumption and production (inverts sign: Enode's `power` = net flow where positive = consumed; the bot displays it as positive = production)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An Enode API account (sandbox or production)
- (Optional) ngrok for local webhook testing

### Installation

```bash
# Clone the repository
cd energychief

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Copy and edit environment variables
cp .env.example .env
# Fill in your TELEGRAM_TOKEN and Enode credentials
```

### Configuration (`.env`)

```ini
# Required
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_REDIRECT_URI="https://t.me/your_bot_username"

# Database (SQLite default, PostgreSQL for production)
DATABASE_URL=sqlite:///db/energychief.db

# Enode — use one environment
ENODE_CLIENT_ID=your_client_id
ENODE_CLIENT_SECRET=your_client_secret
ENODE_API_URL=https://enode-api.sandbox.enode.io    # or .production.enode.io

# Optional — uncomment for webhook mode
# WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app
# ENODE_WEBHOOK_SECRET=your_webhook_secret
```

### Database Setup

```bash
# Create the database and run migrations
uv run alembic upgrade head

# Seed RECs from CSV (done automatically on app startup)
# The file recs_data.csv is loaded when the FastAPI app starts
```

### Running Locally

```bash
# Start the application (polling mode — no webhook needed)
uv run python serve.py
```

The bot will start polling Telegram for updates. Open Telegram and message your bot with `/start`.

### Webhook Mode (for production or Enode events)

```bash
# 1. Start ngrok
ngrok http 8000

# 2. Set WEBHOOK_BASE_URL in .env to your ngrok URL
# 3. Create an Enode webhook subscription
uv run python -m backend.manage_webhooks create

# 4. Restart the app — it will register the Telegram webhook automatically
uv run python serve.py
```

---

## 📡 Enode Integration

Energy Chief connects to Enode's API to read smart meter data. The integration flow:

1. **User links their meter**: User sends `/collegacontatore` → bot creates an Enode link session → user opens the URL and logs into their energy provider.
2. **Data collection** (two channels):
   - **Polling**: Every 60 minutes, `collect_and_store_readings()` fetches all meters via `GET /meters` and saves the latest `energyState`.
   - **Webhooks** (optional): When configured, Enode pushes events in near-real-time (e.g. `user:meter:updated`). Events are HMAC-SHA1 verified and processed.
3. **REC monitoring**: The bot checks aggregate energy availability in the user's REC and sends notifications when thresholds are exceeded.

### Enode Events Handled

| Event Type | Action |
|---|---|
| `user:meter:updated` | Upsert meter, save energy reading |
| `user:meter:discovered` | Upsert meter, save energy reading |
| `user:meter:deleted` | Logged for debugging |
| `enode:webhook:test` | Logged (heartbeat) |

---

## 🗄️ Database Schema

```
recs
├── rec_id         INTEGER PK
├── name           TEXT UNIQUE
├── latitude       REAL
├── longitude      REAL
├── pod_prefix     TEXT
└── created_at     TEXT

users
├── user_id                     INTEGER PK
├── telegram_id                 INTEGER UNIQUE
├── first_name                  TEXT
├── heating                     TEXT          -- "Heat pump" / "Gas boiler" / "Both"
├── electricity_rate            REAL          -- €/kWh
├── gas_rate                    REAL          -- €/Sm³
├── rec_id                      INTEGER FK → recs.rec_id
├── threshold_kwh               REAL DEFAULT 2.0
├── notification_interval_hours INTEGER DEFAULT 4
├── last_notified_at            TEXT
├── created_at                  TEXT
└── updated_at                  TEXT

meters
├── meter_id            TEXT PK
├── owner_user_id       INTEGER FK → users.user_id
├── producer            TEXT
├── model               TEXT
├── consumption_enabled INTEGER DEFAULT 1
├── production_enabled  INTEGER DEFAULT 1
└── linked_at           TEXT

energy_readings
├── meter_id   TEXT PK FK → meters.meter_id
├── timestamp  TEXT PK
├── power_kw   REAL
└── created_at TEXT

webhook_events
├── id          INTEGER PK
├── delivery_id TEXT
├── event_type  TEXT
├── meter_id    TEXT
├── payload     TEXT
└── received_at TEXT
```

---

## 🛠️ Development

### Project Principles

- Code language is English; user interface language is Italian.
- Minimal and clear code: introduce new libraries only when necessary.
- Use `uv` for dependency management: `uv add <package>`.
- Use `user_id` (internal PK) rather than `telegram_id` for identifying users in database operations (unless strictly necessary).
- Debug files go in the `Debug/` folder and should be cleaned up.

### Common Commands

```bash
# Run migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Run the application
uv run python serve.py

# Run a Python module as script
uv run python -m backend.manage_webhooks list

# Add a dependency
uv add <package-name>
```

### Deployment Notes (Uberspace)

The `serve.py` entry point runs Uvicorn on `127.0.0.1:8000`. In production, it's kept alive by Uberspace's supervisord. The `.env` file must be present in the working directory.

---

## 📄 License

MIT — see `LICENSE` file for details.