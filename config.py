import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8680706346:AAFTRDXW5ZoxtRBZRVKvW2FM5l8CkUF0hl4")
PREMIUM_KEY = os.getenv("PREMIUM_KEY", "Sadixll")
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "5"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/sadix_downloads")
DB_PATH = os.getenv("DB_PATH", "sadix_bot.db")
PORT = int(os.getenv("PORT", "8080"))
