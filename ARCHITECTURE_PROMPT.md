# EnergyChief — Prompt implementativo per coding agent

## Obiettivo

Implementa un bot Telegram Python per Comunità Energetiche Rinnovabili (CER).
Il bot notifica i consumer quando un prosumer della loro CER immette energia in eccesso
in rete, e invia ogni mattina un forecast solare.

Il progetto parte come MVP (1 CER, 1 prosumer), ma l'architettura
deve supportare N CER × M prosumer senza modifiche strutturali.

I dati energetici vengono letti tramite **Enode API**, che unifica l'accesso
a contatori di diversi vendor (Huawei, SolarEdge, Enphase, ecc.).
Per il MVP si usa il power meter (energyState.power); in futuro si aggiungeranno
inverter, batterie e altri data point.

---

## Stack tecnologico

| Componente | Libreria | Motivazione |
|---|---|---|
| Bot Telegram | `python-telegram-bot>=21` | Async nativo, `ConversationHandler` per onboarding |
| Scheduler | `apscheduler>=4` | `AsyncIOScheduler`, stessa event loop del bot |
| HTTP client | `httpx` | Async, OAuth2 token management per Enode API |
| Retry | `tenacity` | Backoff esponenziale per API esterne |
| Database | `aiosqlite` + `sqlite3` | Zero-config, WAL mode, file singolo, backup = cp |
| ORM/query | SQL raw con `aiosqlite` | Nessun overhead ORM per MVP |
| Meteo | `openmeteo-requests` | Già usata nel progetto, API senza key |
| Config | `pydantic-settings` | Validazione env vars tipizzata |
| Package manager | `uv` | Già in uso nel progetto |

**Python**: 3.14 (da `.python-version` esistente).

---

## Directory del progetto

```
energychief/
├── pyproject.toml
├── .python-version              # 3.14
├── .env.example
├── .gitignore
├── README.md
├── src/
│   └── energychief/
│       ├── __init__.py
│       ├── __main__.py          # Entry point: crea Application, registra handler e scheduler, run_polling()
│       ├── config.py            # pydantic-settings: Settings da env vars
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── schema.sql       # DDL completo (vedi sotto)
│       │   ├── connection.py    # get_db() → aiosqlite connection, init_db()
│       │   └── repository.py    # Funzioni async CRUD (get_cer_by_prefix, get_members_by_cer, save_reading, ...)
│       │
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── handlers/
│       │   │   ├── __init__.py
│       │   │   ├── start.py         # /start, /help — comandi informativi
│       │   │   ├── onboarding.py    # ConversationHandler multistep (vedi flusso sotto)
│       │   │   ├── settings.py      # /impostazioni — modifica soglie, preferenze notifica
│       │   │   └── status.py        # /stato — mostra ultima lettura, stato CER
│       │   └── messages.py          # Template dei messaggi in italiano (stringhe costanti)
│       │
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py             # ABC EnergyDataAdapter
│       │   └── enode.py            # EnodeAdapter (OAuth2, meters, refresh-hint)
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── polling.py          # poll_all_prosumers(): scheduled ogni 60min 06-22
│       │   ├── notifier.py         # dispatch_surplus_notification(), dispatch_forecast()
│       │   ├── forecast.py         # build_daily_forecast(lat, lon, capacity_kwp) → ore migliori
│       │   └── weather.py          # get_solar_forecast(lat, lon) → DataFrame orario irraggiamento
│       │
│       └── utils/
│           ├── __init__.py
│           └── pod.py              # validate_pod(), extract_pod_prefix()
│
├── tests/                          # Placeholder, non prioritario per MVP
│   └── __init__.py
│
├── Dockerfile
└── _old/                           # Codice esistente, non toccare
```

---

## Schema database (SQLite)

File: `src/energychief/db/schema.sql`

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Comunità Energetica Rinnovabile
CREATE TABLE IF NOT EXISTS cer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    pod_prefix  TEXT    NOT NULL UNIQUE,   -- primi 8 char del POD (identifica cabina primaria)
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Membro (prosumer o consumer)
CREATE TABLE IF NOT EXISTS member (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id        INTEGER NOT NULL UNIQUE,
    telegram_username  TEXT,
    cer_id             INTEGER REFERENCES cer(id),
    role               TEXT    NOT NULL CHECK(role IN ('prosumer', 'consumer')),
    pod                TEXT    NOT NULL,          -- codice POD completo (14 char)
    is_active          INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Configurazione impianto prosumer
CREATE TABLE IF NOT EXISTS prosumer_plant (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id               INTEGER NOT NULL UNIQUE REFERENCES member(id) ON DELETE CASCADE,
    -- Enode: identificativi utente e dispositivi
    enode_user_id           TEXT    NOT NULL UNIQUE,   -- Enode user ID (da Link flow)
    enode_meter_id          TEXT,                      -- UUID del meter Enode (power consumption)
    enode_inverter_id       TEXT,                      -- UUID inverter (futuro: produzione solare)
    enode_battery_id        TEXT,                      -- UUID batteria (futuro)
    -- Impianto
    latitude                REAL    NOT NULL,
    longitude               REAL    NOT NULL,
    capacity_kwp            REAL,                      -- potenza nominale picco
    -- Soglia notifica (il prosumer decide quando segnalare surplus)
    export_threshold_kw     REAL    NOT NULL DEFAULT 1.0,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Preferenze notifica per ogni membro
CREATE TABLE IF NOT EXISTS notification_preference (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id     INTEGER NOT NULL UNIQUE REFERENCES member(id) ON DELETE CASCADE,
    enabled       INTEGER NOT NULL DEFAULT 1,
    min_power_kw  REAL    NOT NULL DEFAULT 0.5,  -- il consumer ignora surplus sotto questa soglia
    quiet_start   TEXT    NOT NULL DEFAULT '22:00',
    quiet_end     TEXT    NOT NULL DEFAULT '06:00',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Serie storica letture energetiche
CREATE TABLE IF NOT EXISTS energy_reading (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prosumer_plant_id   INTEGER NOT NULL REFERENCES prosumer_plant(id) ON DELETE CASCADE,
    timestamp           TEXT    NOT NULL,   -- ISO 8601
    grid_power_kw       REAL,              -- positivo=export, negativo=import
    inverter_power_kw   REAL,
    battery_soc_pct     REAL,
    battery_power_kw    REAL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reading_plant_ts ON energy_reading(prosumer_plant_id, timestamp);

-- Log notifiche inviate (audit + anti-spam)
CREATE TABLE IF NOT EXISTS notification_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cer_id              INTEGER NOT NULL REFERENCES cer(id),
    prosumer_plant_id   INTEGER NOT NULL REFERENCES prosumer_plant(id),
    type                TEXT    NOT NULL CHECK(type IN ('surplus', 'forecast', 'prosumer_confirm')),
    grid_power_kw       REAL,
    recipients_count    INTEGER,
    sent_at             TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Configurazione globale di sistema (K/V)
CREATE TABLE IF NOT EXISTS system_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Valori di default iniziali
INSERT OR IGNORE INTO system_config (key, value) VALUES
    ('default_export_threshold_kw', '1.0'),
    ('polling_interval_minutes', '60'),
    ('polling_start_hour', '6'),
    ('polling_end_hour', '22'),
    ('forecast_hour', '7'),
    ('forecast_minute', '0');
```

---

## Diagramma dei componenti

```
┌─────────────────────────────────────────────────────────────────┐
│                        PROCESSO UNICO (asyncio)                 │
│                                                                 │
│  ┌──────────────────────┐     ┌──────────────────────────────┐  │
│  │  python-telegram-bot │     │   APScheduler (AsyncIO)      │  │
│  │                      │     │                              │  │
│  │  /start              │     │  ┌────────────────────────┐  │  │
│  │  /registra (onboard) │     │  │ Job: poll_all_prosumers│  │  │
│  │  /stato              │     │  │ cron: */60 min, 06-22  │  │  │
│  │  /impostazioni       │     │  └──────────┬─────────────┘  │  │
│  │  /aiuto              │     │             │                │  │
│  └──────────┬───────────┘     │  ┌──────────▼─────────────┐  │  │
│             │                 │  │ Job: send_forecast      │  │  │
│             │                 │  │ cron: 07:00 daily       │  │  │
│             │                 │  └──────────┬─────────────┘  │  │
│             │                 └─────────────┼────────────────┘  │
│             │                               │                   │
│  ┌──────────▼───────────────────────────────▼────────────────┐  │
│  │                    services/                               │  │
│  │                                                            │  │
│  │  polling.py ──→ adapters/enode.py ──→ Enode API (HTTPS)   │  │
│  │      │                  │              ├── POST /meters/   │  │
│  │      │                  │              │    {id}/refresh-  │  │
│  │      │                  │              │    hint            │  │
│  │      │                  │              ├── GET /meters/    │  │
│  │      │                  │              │    {id}            │  │
│  │      │                  │              └── GET /users/     │  │
│  │      │                  │                   {id}/meters    │  │
│  │      │                                                     │  │
│  │      ├──→ notifier.py ──→ bot.send_message() → Telegram   │  │
│  │      │                                                     │  │
│  │      └──→ db/repository.py ──→ SQLite (WAL)               │  │
│  │                                                            │  │
│  │  forecast.py ──→ weather.py ──→ Open-Meteo API (HTTPS)    │  │
│  │      │                                                     │  │
│  │      └──→ notifier.py ──→ bot.send_message() → Telegram   │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Flusso polling (ogni 60 min, 06–22)

```
1. poll_all_prosumers():
   per ogni prosumer_plant attivo nel DB:
     2. adapter = EnodeAdapter(enode_user_id, enode_meter_id, settings)
     3. adapter.refresh_hint()  → POST /meters/{meterId}/refresh-hint
     4. await asyncio.sleep(3)  → attendi propagazione dati
     5. meter_data = adapter.get_meter()  → GET /meters/{meterId}
     6. reading.grid_power_kw = -meter_data.energyState.power  (converti segno)
        → Enode: positivo = import da rete, negativo = export a rete
        → Noi:   positivo = export a rete, negativo = import da rete
     7. save_reading(plant_id, reading) nel DB
     8. SE reading.grid_power_kw > plant.export_threshold_kw:
        a. notifier.notify_prosumer(plant, reading)
        b. consumers = get_active_consumers(plant.cer_id)
        c. per ogni consumer (filtrato per min_power_kw e quiet hours):
           notifier.notify_consumer(consumer, reading)
        d. log_notification(cer_id, plant_id, 'surplus', reading, count)
```
1. poll_all_prosumers():
   per ogni prosumer_plant attivo nel DB:
     2. adapter = EnodeAdapter(enode_user_id, enode_meter_id, settings)
     3. adapter.refresh_hint()  → POST /meters/{meterId}/refresh-hint
     4. await asyncio.sleep(3)  → attendi propagazione dati
     5. meter_data = adapter.get_meter()  → GET /meters/{meterId}
     6. reading.grid_power_kw = -meter_data.energyState.power  (converti segno)
        → Enode: positivo = import da rete, negativo = export a rete
        → Noi:   positivo = export a rete, negativo = import da rete
     7. save_reading(plant_id, reading) nel DB
     8. SE reading.grid_power_kw > plant.export_threshold_kw:
        a. notifier.notify_prosumer(plant, reading)
        b. consumers = get_active_consumers(plant.cer_id)
        c. per ogni consumer (filtrato per min_power_kw e quiet hours):
           notifier.notify_consumer(consumer, reading)
        d. log_notification(cer_id, plant_id, 'surplus', reading, count)
```

### Flusso forecast (07:00 daily)

```
1. send_forecast():
   per ogni CER con almeno un prosumer attivo:
     2. per ogni prosumer_plant della CER:
        a. forecast = build_daily_forecast(lat, lon, capacity_kwp)
           → chiama Open-Meteo per shortwave_radiation orario di oggi
           → stima produzione_kw[h] = irradiance[h] × capacity_kwp × efficiency
           → efficiency calibrata da media storica (energy_reading) o default 0.15
        b. aggrega i forecast di tutti i prosumer della CER
     3. best_hours = top 4 ore con maggiore produzione stimata
     4. members = get_all_active_members(cer_id)
     5. per ogni member: notifier.send_forecast_message(member, best_hours)
```

---

## Adapter pattern per dati energetici

File `src/energychief/adapters/base.py`:

```python
# ABC — interfaccia che ogni adapter deve implementare

class EnergyDataAdapter(ABC):
    """Interfaccia astratta per leggere dati energetici da Enode."""

    @abstractmethod
    async def get_grid_power_kw(self) -> float | None:
        """Potenza netta al punto di connessione. >0 = export, <0 = import. None se non disponibile."""

    @abstractmethod
    async def get_inverter_power_kw(self) -> float | None:
        """Potenza prodotta dall'inverter. None se non disponibile."""

    @abstractmethod
    async def get_battery_status(self) -> dict | None:
        """{'soc_pct': float, 'power_kw': float} o None se non presente."""

    @abstractmethod
    async def discover_devices(self) -> dict:
        """Discovery dispositivi Enode. Ritorna dict con meter_id, inverter_id, battery_id."""
```

L'adapter Enode (`enode.py`) implementa questa ABC usando `httpx.AsyncClient`
con OAuth2 client credentials grant. Il token viene cachato e refreshato
automaticamente ogni ~55 minuti (scade dopo 1 ora).

**Importante nell'implementazione Enode:**
- OAuth2 token: `POST https://oauth.{env}.enode.io/oauth2/token` con client_id:client_secret
- Token response: `{"access_token": "...", "expires_in": 3599}` — cachare fino a scadenza
- Meter data: `GET /meters/{meterId}` → `energyState.power` (kW)
  - **Positivo** = importa da rete (consumo netto)
  - **Negativo** = esporta a rete (produzione in eccesso)
- Refresh hint: `POST /meters/{meterId}/refresh-hint` → trigger refresh accelerato
  - Usare con cautela: attendere ~2-5 secondi prima di leggere i dati
  - Enode mantiene i dati aggiornati automaticamente (~10 min cache),
    il refresh-hint serve solo per letture on-demand
- Discovery: `GET /users/{userId}/meters` → lista meter associati all'utente
- `energyState.power: null` → ritorna `None` (skip lettura)
- `isReachable: false` → dati potenzialmente ritardati, log warning
- Scopes richiesti: `meter:read:data` (obbligatorio), `meter:read:location` (opzionale)
- Ambienti: `sandbox` → `enode-api.sandbox.enode.io`, `production` → `enode-api.production.enode.io`

Per aggiungere nuovi data point in futuro:
- Batterie: `GET /batteries/{batteryId}` → `chargeState.batteryLevel`, `chargeState.chargeRate`
- Inverter solari: `GET /inverters/{inverterId}` → produzione solare
- HEM systems: `GET /hems/{hemId}` → dati aggregati home energy management

---

## Onboarding conversazionale

Implementa con `ConversationHandler` di python-telegram-bot.

**Comando:** `/registra`

**Stati del ConversationHandler:**

```
ROLE → POD → [se prosumer: ENODE_LINK → DEVICE_CONFIRM → COORDINATES → CAPACITY → THRESHOLD]
      → [se consumer: verifica CER esistente da pod_prefix]
      → NOTIFICATION_PREFS → CONFIRM → END
```

**Dettagli per stato:**

1. **ROLE**: "Sei un prosumer (hai un impianto FV) o un consumer?"
   → Bottoni inline: `[Prosumer]` `[Consumer]`

2. **POD**: "Inserisci il tuo codice POD (formato IT001E12345678)"
   → Validazione: regex `^IT\d{3}E\d{8}$`, 14 caratteri.
   → Estrai `pod_prefix = pod[:8]`.
   → Cerca CER con quel prefix. Se non esiste e il ruolo è prosumer,
     creala automaticamente. Se consumer e CER non esiste, messaggio
     "Nessuna CER trovata per la tua cabina primaria. Contatta l'admin."

3. **ENODE_LINK** (solo prosumer):
   → Il bot genera un Enode Link URL con scope `meter:read:data`:
     `https://link.{env}.enode.io?client_id={id}&user_id={telegram_id}&scopes=meter:read:data`
   → Mostra all'utente: "Apri questo link per collegare il tuo contatore: {url}"
   → Inline button `[Ho completato il collegamento]`
   → Al click: `GET /users/{userId}/meters` per scoprire i meter associati
   → Se nessun meter trovato: "Nessun contatore trovato. Riprova il collegamento."
   → Se un solo meter: salva automaticamente `enode_meter_id`
   → Se più meter: mostra lista con bottoni, utente sceglie quello corretto
   → Se il meter ha coordinate (location.latitude/longitude), proponile come default

4. **COORDINATES**: "Coordinate dell'impianto (lat, lon)" — pre-compilato da Enode location se disponibile.

5. **CAPACITY**: "Potenza nominale dell'impianto in kWp" (opzionale, serve per forecast).

6. **THRESHOLD**: "Soglia di export in kW per inviare notifiche ai consumer (default: 1.0)"

7. **NOTIFICATION_PREFS**: per tutti.
   → min_power_kw, quiet hours. Mostra default, ok per confermare.

8. **CONFIRM**: riepilogo dati → bottoni `[Conferma]` `[Modifica]` `[Annulla]`

**Comando `/impostazioni`** per modifiche successive: mostra menu con bottoni per
ogni parametro modificabile (soglia, preferenze notifica).

---

## Gestione configurazione

File `src/energychief/config.py` con `pydantic-settings`:

```
TELEGRAM_BOT_TOKEN: str              # token da BotFather
ENODE_CLIENT_ID: str                 # client ID da dashboard Enode
ENODE_CLIENT_SECRET: str             # client secret da dashboard Enode
ENODE_ENVIRONMENT: str = "sandbox"   # sandbox o production
DATABASE_PATH: str = "data/energychief.db"  # path file SQLite
LOG_LEVEL: str = "INFO"
```

Tutte le altre configurazioni (soglie, orari polling/forecast) vengono dalla
tabella `system_config` nel DB, così sono modificabili a runtime senza restart.

File `.env.example`:
```
TELEGRAM_BOT_TOKEN=
ENODE_CLIENT_ID=
ENODE_CLIENT_SECRET=
ENODE_ENVIRONMENT=sandbox
DATABASE_PATH=data/energychief.db
LOG_LEVEL=INFO
```
TELEGRAM_BOT_TOKEN: str              # token da BotFather
ENODE_CLIENT_ID: str                 # client ID da dashboard Enode
ENODE_CLIENT_SECRET: str             # client secret da dashboard Enode
ENODE_ENVIRONMENT: str = "sandbox"   # sandbox o production
DATABASE_PATH: str = "data/energychief.db"  # path file SQLite
LOG_LEVEL: str = "INFO"
```

Tutte le altre configurazioni (soglie, orari polling/forecast) vengono dalla
tabella `system_config` nel DB, così sono modificabili a runtime senza restart.

File `.env.example`:
```
TELEGRAM_BOT_TOKEN=
ENODE_CLIENT_ID=
ENODE_CLIENT_SECRET=
ENODE_ENVIRONMENT=sandbox
DATABASE_PATH=data/energychief.db
LOG_LEVEL=INFO
```

---

## Logica anti-spam notifiche

Per evitare di notificare ogni 60 minuti se il surplus persiste:
- Dopo aver inviato una notifica `surplus`, registra in `notification_log`.
- Al ciclo successivo, se il surplus persiste, invia **solo se** l'ultima notifica
  surplus per quella CER è stata inviata **più di 3 ore fa** OPPURE se la potenza
  è aumentata di **>50%** rispetto all'ultima notifica.
- Quando il surplus finisce (grid_power torna sotto soglia), invia un messaggio
  breve di fine surplus ("L'eccesso è terminato") — opzionale, solo se c'era
  stata una notifica attiva.

---

## Forecast mattutino — logica

1. Chiama Open-Meteo Forecast API (non archive):
   `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=shortwave_radiation&forecast_days=1`
2. Per ogni ora del giorno: `estimated_kw[h] = shortwave_radiation[h] / 1000 * capacity_kwp * 0.80`
   (0.80 = performance ratio approssimato; in futuro calibrabile da dati storici)
3. Filtra ore con estimated_kw > 0.5
4. Formatta messaggio: "☀️ Previsione solare per oggi:\n• 10:00-11:00 — ~3.2 kW\n• 11:00-12:00 — ~3.8 kW\n..."
5. Aggiungi consiglio: "Le ore migliori per usare elettrodomestici energivori sono ..."

Se una CER ha più prosumer, somma i forecast di tutti gli impianti.

---

## Mensaggi utente (italiano)

Tutti i messaggi del bot devono essere in italiano. Tono: informale ma chiaro.
Usa emoji per leggibilità (⚡ ☀️ 🔋 🏠 ✅ ❌ ⚙️).

Esempi chiave:
- Surplus: "⚡ Energia disponibile nella tua CER!\n{prosumer_name} sta immettendo {power} kW in rete.\nÈ un buon momento per attivare lavatrice, lavastoviglie o ricarica EV!"
- Conferma prosumer: "☀️ Stai immettendo {power} kW in rete. Ho avvisato {n} membri della CER!"
- Forecast: "☀️ Previsione solare per oggi ({date}):\n{ore_formattate}\n\n💡 Consiglio: programma gli elettrodomestici nelle fasce evidenziate."
- Fine surplus: "ℹ️ L'eccesso di energia nella CER è terminato."

---

## Deployment

### Opzione raccomandata: Railway.app

- Pro: deploy da Git push, $5/mo di crediti nel free trial, supporta processi long-running, env vars dalla dashboard.
- Il bot gira come worker process (non web server): configura `Procfile` con `worker: uv run python -m energychief`
- SQLite file su disco persistente (Railway supporta persistent volumes).

### Alternativa economica: Hetzner VPS CX22

- €3.49/mo, 2 vCPU, 4GB RAM (overkill, ma il più economico).
- Deploy: `git clone` + `uv sync` + `systemd` service.

### Alternativa free: Oracle Cloud Free Tier

- VM ARM free forever, 1 GB RAM sufficiente.
- Setup più complesso.

### File Dockerfile (per Railway o qualsiasi container host)

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --frozen
CMD ["uv", "run", "python", "-m", "energychief"]
```

### File Procfile (per Railway)

```
worker: uv run python -m energychief
```

### Persistenza SQLite in cloud

Il file SQLite deve risiedere su un volume persistente. Su Railway: monta un volume
su `/app/data/`. Se il provider non supporta volumi persistenti, migra a PostgreSQL
(Neon.tech o Supabase offrono tier gratuiti) — ma per MVP SQLite è preferibile.

---

## Entry point (`__main__.py`)

Sequenza di avvio:

```
1. Carica Settings da env vars
2. init_db(): crea tabelle se non esistono (esegui schema.sql)
3. Crea Application (python-telegram-bot)
4. Registra handler: start, onboarding ConversationHandler, settings, status
5. Crea AsyncIOScheduler (APScheduler)
6. Aggiungi job: poll_all_prosumers (cron ogni 60 min, 06-22 CET)
7. Aggiungi job: send_forecast (cron 07:00 CET daily)
8. Avvia scheduler
9. application.run_polling()  ← questo blocca e gestisce il loop asyncio
```

**Nota sul timezone:** tutti gli orari dello scheduler devono essere in `Europe/Rome`.
Il database salva timestamp in UTC (ISO 8601). La conversione avviene nella
presentazione (messaggi all'utente).

---

## Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Enode API rate limit (429) | Lettura fallita | Retry con tenacity (3 tentativi, backoff). Log warning. Non notificare errori agli utenti. |
| Enode data freshness (~10 min cache) | Dati non real-time | `refresh-hint` prima di ogni lettura. Delay ~2-5 min per propagazione. Accettabile per MVP. |
| Enode Link flow non completato | Onboarding bloccato | Timeout dopo 10 min, messaggio all'utente di riprovare. |
| Meter non raggiungibile (`isReachable: false`) | Dati ritardati | Log warning, skip notifica. Riprova al ciclo successivo. |
| SQLite lock in scrittura | Improbabile con processo singolo | WAL mode + unico writer (processo singolo) |
| Open-Meteo down | Forecast non inviato | Retry. Se fallisce, skip con log. Il forecast non è critico. |
| Prosumer offline (meter spento) | `energyState.power: null` | Gestito: `None` = skip, nessuna notifica. |

---

## NOTE PER IL CODING AGENT

- **Leggi la documentazione Enode API** a https://developers.enode.com/api/reference
  prima di implementare `adapters/enode.py`. Contiene tutti gli endpoint, campi,
  scopes e webhook events per meters, batteries, inverters.
- Non toccare la cartella `_old/` — è codice legacy non correlato.
- Usa `uv` per gestire dipendenze (`pyproject.toml`).
- I test non sono prioritari per l'MVP, ma struttura il codice per essere testabile
  (dependency injection degli adapter, repository separato dal business logic).
- Tutti i file Python devono avere docstring di modulo in italiano.
- Tipo annotazioni ovunque (Python 3.14, usa `type X = ...` syntax dove appropriato).
- Gestisci graceful shutdown: lo scheduler e il bot devono chiudersi pulitamente su SIGTERM.
- **Enode Link UI**: per il MVP, genera l'URL manualmente e presentalo all'utente.
  In futuro si può integrare un webhook endpoint per ricevere eventi di completamento.
- **Conversione segno potenza**: Enode usa positivo=import, negativo=export.
  Il bot usa positivo=export, negativo=import. Converti sempre nell'adapter:
  `grid_power_kw = -meter_data.energyState.power`.
- **Enode Link UI**: per il MVP, genera l'URL manualmente e presentalo all'utente.
  In futuro si può integrare un webhook endpoint per ricevere eventi di completamento.
