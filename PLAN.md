# PLAN.md — Deferred Technical Debt

Issues identified during codebase audit (2026-06-18) that are *not* tackled
in the current critical-fix cycle. These are prioritised for future sprints.

---

## 🟡 MEDIUM — Deferred

### 1. `/setup` conversation incomplete — only collects POD + REC

**Files**: `frontend/handlers/setup.py`, `shared/models.py`

The `User` model defines `threshold_kwh`, `notification_interval_hours` but the
`/setup` conversation never collects them. They default to 2.0 kWh and 4 hours
in the DB and are used as-is. A future setup step should let users configure
these values per their preference.

The `frontend/validators.py` module (`parse_positive_float`) was written for
this purpose and is currently dead code.

**Action**: Add `ASK_THRESHOLD` / `ASK_INTERVAL` conversation states + keyboard
choices so users can personalise notification behaviour.

---

### 2. Dead code: `frontend/validators.py`

**File**: `frontend/validators.py`

`parse_positive_float()` is defined but never imported or called. It was
intended for validating electricity/gas rate input in a now-removed setup step.

**Action**: Either wire it into threshold/interval validation (see #1 above) or
remove the file entirely.

---

### 3. Naive UTC datetime strings stored in the database

**Files**: `shared/database.py` (line 50), `frontend/telegram_app.py` (line ~65-75)

`datetime.utcnow().isoformat()` produces timezone-naive strings. Every call site
that compares these to aware datetimes must manually attach `timezone.utc`
(e.g. the `if last_at.tzinfo is None` workaround in `check_recs_and_notify`).
This is fragile and will break silently in any future code that reads these
columns.

**Action**: Store datetimes as UTC-aware ISO strings (e.g. using
`datetime.now(timezone.utc).isoformat()`). Update all comparison code to remove
the manual `replace()` workaround. Alternatively, use SQLAlchemy's `DateTime`
type with `timezone=True` instead of `String` for timestamp columns.

---

### 4. `get_latest_reading_for_meter` silently returns `None` after 20 consecutive NaN

**File**: `shared/database.py` (line ~148-163)

The function scans at most 20 readings looking for non-NaN power values. If
Enode sends 20+ consecutive NaN readings, valid readings beyond position 20 are
silently skipped, and the caller gets `None` — indistinguishable from "no
readings at all."

**Action**: Increase the scan window or add a `power_kw IS NOT NULL` /
`power_kw != 'NaN'` filter at the SQL level. Document the limit or remove it.

---

## 🔵 LOW — Deferred

### 5. Global mutable state for OAuth token cache

**File**: `backend/enode_api.py`

Module-level globals `_token` and `_token_expires_at`, with lazy credentials
initialisation. Works in single-asyncio-loop FastAPI but would be a race
condition under any concurrency.

**Action**: Wrap in a simple class or use `contextvars` / `asyncio.Lock` if
concurrent access is ever needed. Reuse `httpx.AsyncClient` instance across
calls instead of creating a new one per request.

---

### 6. Imports inside lifespan function

**File**: `app.py` (lines 24-25)

```python
from shared.engine import engine
from shared.models import Base
```

These are inside `lifespan()`. Move to module-level imports.

---

### 7. Dead configuration in `.env`

**File**: `.env`

`ENODESAND_CLIENT_ID`, `ENODESAND_CLIENT_SECRET`, `ENODESAND_API_URL` are
defined but never read. Only the production `ENODE_*` variants are used.

**Action**: Remove or add a sandbox toggle to `shared/config.py`.

---

### 8. Missing index on `energy_readings(meter_id, timestamp DESC)`

**File**: `shared/database.py` (`get_latest_power_per_meter`)

The raw SQL uses a correlated subquery:
```sql
WHERE er.timestamp = (SELECT MAX(timestamp) FROM energy_readings WHERE meter_id = er.meter_id)
```

Without an index on `(meter_id, timestamp)`, this degrades to a table scan as
readings accumulate.

**Action**: Add an explicit index on `energy_readings(meter_id, timestamp)` via
a new Alembic migration. The compound primary key `(meter_id, timestamp)` may
already provide an index depending on the database, but a DESC index or
explicit composite index is safer.
