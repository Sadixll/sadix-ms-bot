import sqlite3
import datetime
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0,
            premium INTEGER DEFAULT 0,
            last_reset TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id: int) -> dict:
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count, premium, last_reset FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute(
            "INSERT INTO users (user_id, count, premium, last_reset) VALUES (?, 0, 0, ?)",
            (user_id, today)
        )
        conn.commit()
        row = (0, 0, today)
    count, premium, last_reset = row
    if last_reset != today:
        c.execute("UPDATE users SET count=0, last_reset=? WHERE user_id=?", (today, user_id))
        conn.commit()
        count = 0
    conn.close()
    return {"count": count, "premium": bool(premium)}


def increment_count(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET count = count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def set_premium(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET premium=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
