PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Renewable Energy Community (CER)
CREATE TABLE IF NOT EXISTS cer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    pod_prefix  TEXT    NOT NULL UNIQUE,   -- first 8 chars of the POD
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Member (prosumer or consumer)
CREATE TABLE IF NOT EXISTS member (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id        INTEGER NOT NULL UNIQUE,
    telegram_username  TEXT,
    cer_id             INTEGER REFERENCES cer(id),
    role               TEXT    NOT NULL CHECK(role IN ('prosumer', 'consumer')),
    pod                TEXT    NOT NULL,          -- full 14 char POD code
    is_active          INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Prosumer plant configuration
CREATE TABLE IF NOT EXISTS prosumer_plant (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id               INTEGER NOT NULL UNIQUE REFERENCES member(id) ON DELETE CASCADE,
    -- Enode: user and device identifiers
    enode_user_id           TEXT    NOT NULL UNIQUE,   -- Enode user ID
    enode_meter_id          TEXT,                      -- Enode meter UUID
    enode_inverter_id       TEXT,                      -- Enode inverter UUID
    enode_battery_id        TEXT,                      -- Enode battery UUID
    -- Plant details
    latitude                REAL    NOT NULL,
    longitude               REAL    NOT NULL,
    capacity_kwp            REAL,                      -- peak nominal capacity
    -- Notification threshold
    export_threshold_kw     REAL    NOT NULL DEFAULT 1.0,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Notification preferences for each member
CREATE TABLE IF NOT EXISTS notification_preference (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id     INTEGER NOT NULL UNIQUE REFERENCES member(id) ON DELETE CASCADE,
    enabled       INTEGER NOT NULL DEFAULT 1,
    min_power_kw  REAL    NOT NULL DEFAULT 0.5,
    quiet_start   TEXT    NOT NULL DEFAULT '22:00',
    quiet_end     TEXT    NOT NULL DEFAULT '06:00',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Historical energy readings
CREATE TABLE IF NOT EXISTS energy_reading (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prosumer_plant_id   INTEGER NOT NULL REFERENCES prosumer_plant(id) ON DELETE CASCADE,
    timestamp           TEXT    NOT NULL,   -- ISO 8601
    grid_power_kw       REAL,              -- positive=export, negative=import
    inverter_power_kw   REAL,
    battery_soc_pct     REAL,
    battery_power_kw    REAL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reading_plant_ts ON energy_reading(prosumer_plant_id, timestamp);

-- Notification logs
CREATE TABLE IF NOT EXISTS notification_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cer_id              INTEGER NOT NULL REFERENCES cer(id),
    prosumer_plant_id   INTEGER NOT NULL REFERENCES prosumer_plant(id),
    type                TEXT    NOT NULL CHECK(type IN ('surplus', 'forecast', 'prosumer_confirm')),
    grid_power_kw       REAL,
    recipients_count    INTEGER,
    sent_at             TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Global system configuration (K/V)
CREATE TABLE IF NOT EXISTS system_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Default initial values
INSERT OR IGNORE INTO system_config (key, value) VALUES
    ('default_export_threshold_kw', '1.0'),
    ('polling_interval_minutes', '60'),
    ('polling_start_hour', '6'),
    ('polling_end_hour', '22'),
    ('forecast_hour', '7'),
    ('forecast_minute', '0');
