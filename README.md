# EnergyChief ⚡

EnergyChief is a Telegram bot designed for **Renewable Energy Communities (CER)**. It empowers consumers by notifying them when a prosumer in their community is exporting excess solar energy to the grid, and provides daily solar forecasts to optimize energy usage.

The project is built with a scalable architecture, starting from an MVP (Minimum Viable Product) and designed to support $N$ Communities $\times$ $M$ Prosumers without structural changes.

---

## 🚀 Key Features

- **Real-time Surplus Notifications**: Notifies consumers when a prosumer's export exceeds a defined threshold.
- **Daily Solar Forecast**: Sends a morning report with the best hours for heavy appliance usage based on weather data.
- **Automated Onboarding**: A conversational Telegram flow to register both prosumers and consumers.
- **Enode Integration**: Unified access to various energy hardware (Huawei, SolarEdge, Enphase, etc.) via the Enode API.
- **Smart Polling**: Periodic data collection with automated "refresh hints" to ensure data freshness.

---

## 🛠 Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.14 |
| **Bot Framework** | `python-telegram-bot` (Async) |
| **Task Scheduler** | `apscheduler` (AsyncIO) |
| **API Client** | `httpx` (Async) |
| **Database** | `SQLite` with `aiosqlite` (WAL Mode) |
| **Data Management**| `pydantic-settings`, `pandas` |
| **Package Manager**| `uv` |
| **Weather Data** | `Open-Meteo API` |
| **Energy Data** | `Enode API` |

---

## 📂 Project Structure

```text
energychief/
├── data/                   # SQLite database file
├── src/
│   └── energychief/
│       ├── adapters/       # External API adapters (Enode)
│       ├── bot/            # Telegram handlers and message templates
│       ├── db/             # Database connection and repository (CRUD)
│       ├── services/       # Business logic (Polling, Forecast, Weather, Notifier)
│       ├── utils/          # Helper functions (POD validation)
│       ├── config.py       # Environment settings
│       └── __main__.py     # Entry point
├── pyproject.toml          # Dependencies (uv)
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Recommended package manager)
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Enode API Credentials (Client ID and Client Secret)

### 1. Clone the repository
```bash
git clone <<repositoryrepository-url>
cd energychief
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ENODE_CLIENT_ID=your_enode_client_id
ENODE_CLIENT_SECRET=your_enode_client_secret
ENODE_ENVIRONMENT=production
DATABASE_PATH=data/energychief.db
LOG_LEVEL=INFO
```

### 3. Install Dependencies
Using `uv`:
```bash
uv sync
```

### 4. Run the Bot
```bash
uv run python -m energychief
```

---

## 📈 Future Development Roadmap

The architecture is designed to allow the following expansions:

### 1. Hardware Expansion (Adapters)
- **Battery Management**: Integrate battery SOC (State of Charge) and charge/discharge rates to provide more intelligent surplus notifications.
- **Inverter Monitoring**: Track specific solar production data to improve forecast accuracy.
- **HEMS Integration**: Support Home Energy Management Systems for direct control of appliances.

### 2. Intelligence & Analytics (Services)
- **ML-based Forecasting**: Replace the simple irradiance-based model with Machine Learning models trained on historical `energy_reading` data.
- **Smart Scheduling**: Instead of just notifying, suggest exact times for appliance activation based on real-time grid state.
- **Anti-Spam Logic**: Implement more sophisticated notification throttling (e.g., only notify if power increases by >50% or after 3 hours).

### 3. User Experience (Bot)
- **Web Dashboard**: A frontend to visualize energy trends, CER status, and user settings.
- **Webhook Integration**: Transition from polling to Enode webhooks for near-instantaneous surplus detection.
- **Multi-Language Support**: Extend the `messages.py` to support English, German, etc.

### 4. Scalability (Infrastructure)
- **Database Migration**: Move from SQLite to PostgreSQL (e.g., Supabase or Neon) for high-concurrency production environments.
- **Microservices**: Separate the Polling Service and the Telegram Bot into different containers/services to scale them independently.

---

## 📝 License
[Specify your license here, e.g., MIT]
