# config.py
import os
from dotenv import load_dotenv
import pathlib

load_dotenv()  # reads .env into os.environ

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
DB_PATH: pathlib.Path = pathlib.Path(os.getenv("DB_PATH", "energychief.db"))

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")
