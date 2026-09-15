import sqlite3
import datetime
import asyncio
from typing import Dict, Tuple, Any
from config import DB_PATH, FREE_DAILY_LIMIT

def _get_current_date() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_premium INTEGER DEFAULT 0,
            downloads_today INTEGER DEFAULT 0,
            last_download_date TEXT,
            total_downloads INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            title TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def _sync_get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
    today = _get_current_date()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, is_premium, downloads_today, last_download_date, total_downloads, created_at)
            VALUES (?, ?, ?, 0, 0, ?, 0, ?)
        """, (user_id, username or "", first_name or "", today, now_iso))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    else:
        if row["last_download_date"] != today:
            cursor.execute("""
                UPDATE users
                SET downloads_today = 0, last_download_date = ?, username = ?, first_name = ?
                WHERE user_id = ?
            """, (today, username or row["username"], first_name or row["first_name"], user_id))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        else:
            if username != row["username"] or first_name != row["first_name"]:
                cursor.execute("UPDATE users SET username = ?, first_name = ? WHERE user_id = ?", 
                               (username or row["username"], first_name or row["first_name"], user_id))
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                
    result = dict(row)
    conn.close()
    return result

def _sync_can_download(user_id: int, username: str = None, first_name: str = None) -> Tuple[bool, int, bool]:
    user = _sync_get_or_create_user(user_id, username, first_name)
    if user["is_premium"]:
        return True, 999999, True
    remaining = max(0, FREE_DAILY_LIMIT - user["downloads_today"])
    return remaining > 0, remaining, False

def _sync_increment_download(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET downloads_today = downloads_today + 1,
            total_downloads = total_downloads + 1
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def _sync_activate_premium(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def _sync_log_action(user_id: int, username: str, url: str, title: str, status: str):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (user_id, username, url, title, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username or "", url, title or "", status, now_iso))
    conn.commit()
    conn.close()

def _sync_get_stats() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
    premium_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_downloads) FROM users")
    total_downloads = cursor.fetchone()[0] or 0
    conn.close()
    return {"total_users": total_users, "premium_users": premium_users, "total_downloads": total_downloads}

async def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
    return await asyncio.to_thread(_sync_get_or_create_user, user_id, username, first_name)

async def check_download_limit(user_id: int, username: str = None, first_name: str = None) -> Tuple[bool, int, bool]:
    return await asyncio.to_thread(_sync_can_download, user_id, username, first_name)

async def record_successful_download(user_id: int, username: str, url: str, title: str):
    await asyncio.to_thread(_sync_increment_download, user_id)
    await asyncio.to_thread(_sync_log_action, user_id, username, url, title, "SUCCESS")

async def record_failed_download(user_id: int, username: str, url: str, error_msg: str):
    await asyncio.to_thread(_sync_log_action, user_id, username, url, error_msg, "FAILED")

async def activate_user_premium(user_id: int) -> bool:
    return await asyncio.to_thread(_sync_activate_premium, user_id)

async def get_system_stats() -> Dict[str, Any]:
    return await asyncio.to_thread(_sync_get_stats)
