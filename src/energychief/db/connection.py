import aiosqlite
import logging
from pathlib import Path
from src.energychief.config import settings

logger = logging.getLogger(__name__)

async def get_db():
    """
    Yields an aiosqlite connection.
    """
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    """
    Initializes the database by running the schema.sql script.
    """
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    schema_path = Path("src/energychief/db/schema.sql")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    schema_sql = schema_path.read_text()
    
    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(schema_sql)
        await db.commit()
        logger.info("Database initialized successfully.")
