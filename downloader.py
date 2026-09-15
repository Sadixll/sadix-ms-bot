import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from config import DOWNLOAD_DIR, MAX_FILE_SIZE_MB, DOWNLOAD_TIMEOUT

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
logger = logging.getLogger("sadix_ms.downloader")
MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _download_video_sync(url: str) -> Dict[str, Any]:
    import yt_dlp

    unique_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"{unique_id}_%(id)s.%(ext)s")
    cookie_file = "cookies.txt" if os.path.isfile("cookies.txt") else None

    ydl_opts = {
        'format': 'best[ext=mp4]/best[height<=720]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr', 'web_safari', 'web']
            }
        },
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        }
    }

    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return {"success": False, "error": "Не удалось извлечь видео."}

            if "entries" in info:
                entries = list(info["entries"])
                if not entries:
                    return {"success": False, "error": "Плейлист пуст."}
                info = entries[0]

            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            possible_files = [filename, f"{base}.mp4", f"{base}.mkv", f"{base}.webm"]

            filepath = None
            for candidate in possible_files:
                if os.path.isfile(candidate):
                    filepath = candidate
                    break

            if not filepath:
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.startswith(unique_id):
                        filepath = os.path.join(DOWNLOAD_DIR, f)
                        break

            if not filepath or not os.path.isfile(filepath):
                return {"success": False, "error": "Файл не сохранился."}

            filesize = os.path.getsize(filepath)
            if filesize > MAX_BYTES:
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                return {
                    "success": False,
                    "error": f"Размер видео ({filesize / (1024*1024):.1f} МБ) превышает лимит Telegram (50 МБ)."
                }

            return {
                "success": True,
                "filepath": filepath,
                "title": info.get("title", "Sadix MS Video"),
                "duration": info.get("duration", 0),
                "width": info.get("width"),
                "height": info.get("height"),
                "filesize": filesize
            }
    except Exception as e:
        err = str(e)
        return {"success": False, "error": f"Ошибка: {err.split(';')[0][:250]}"}


async def download_video(url: str, timeout: int = DOWNLOAD_TIMEOUT) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_download_video_sync, url),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {"success": False, "error": "Таймаут скачивания (3 минуты)."}


def cleanup_file(filepath: Optional[str]):
    if filepath and os.path.isfile(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass
