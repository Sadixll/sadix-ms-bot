import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8680706346:AAFTRDXW5ZoxtRBZRVKvW2FM5l8CkUF0hl4")
PREMIUM_CODE = "Sadixll"
FREE_LIMIT = 5
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE_MB = 50
DOWNLOAD_TIMEOUT = 180
DB_PATH = "users.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")
