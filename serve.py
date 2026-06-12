"""Production server entry point — kept alive by Uberspace supervisord.

Run locally:
    uv run python serve.py

On Uberspace, supervisord calls this automatically (see supervisor.ini).
The .env file is loaded by shared/config.py on import — keep it in CWD.
"""
import uvicorn

uvicorn.run(
    "app:app",
    host="127.0.0.1",
    port=8000,
    log_level="info",
    access_log=True,
)