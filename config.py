# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")
