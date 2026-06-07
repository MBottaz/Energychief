# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "")
ENODE_WEBHOOK_SECRET: str = os.getenv("ENODE_WEBHOOK_SECRET", "")

ENODE_API_URL: str = os.getenv("ENODE_API_URL", "https://enode-api.production.enode.io")
REDIRECT_URI: str = os.getenv("TELEGRAM_REDIRECT_URI", "")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")