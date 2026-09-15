import os
import re
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, PREMIUM_KEY, FREE_DAILY_LIMIT, PORT
import database
from downloader import download_video, cleanup_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sadix_ms.bot")

URL_REGEX = re.compile(r'https?://[^\s]+')

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def get_main_keyboard(is_premium: bool) -> InlineKeyboardMarkup:
    buttons = []
    if not is_premium:
        buttons.append([InlineKeyboardButton(text="💎 Активировать премиум", callback_data="buy_premium")])
    buttons.append([
        InlineKeyboardButton(text="📊 Мой статус", callback_data="check_status"),
        InlineKeyboardButton(text="💀 Поддерживаемые сети", callback_data="supported_sites")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    user = await database.get_or_create_user(user_id, username, first_name)
    is_prem = bool(user["is_premium"])
    rem = max(0, FREE_DAILY_LIMIT - user["downloads_today"])
    status_text = "🔥 ПРЕМИУМ (БЕЗЛИМИТ 💎)" if is_prem else f"⚡ БЕСПЛАТНЫЙ ({rem}/{FREE_DAILY_LIMIT} на сегодня)"
    
    welcome_text = (
        "😈 Привет! Я Sadix MS — твой личный загрузчик видео!\n"
        "🎬 Скачиваю из YouTube, TikTok, Instagram, Twitter, Facebook, VK и других сетей.\n"
        "🔓 Работаю даже с защищёнными видео.\n"
        "📥 Просто отправь мне ссылку — и я скачаю.\n"
        "💎 Премиум: бесконечные скачивания.\n"
        "😈 Ворм на связи!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💀 <b>ТВОЙ СТАТУС В SADIX MS:</b>\n"
        f"👤 Пользователь: <b>{message.from_user.full_name}</b>\n"
        f"👑 Статус: <b>{status_text}</b>\n"
        f"📊 Всего скачано: <b>{user['total_downloads']}</b> видео\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <i>Отправь мне любую ссылку на видео прямо сейчас!</i>"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_prem))

@dp.message(Command("premium"))
async def cmd_premium(message: types.Message):
    user_id = message.from_user.id
    args = message.text.strip().split(maxsplit=1)
    
    if len(args) > 1 and args[1].strip() == PREMIUM_KEY:
        await database.activate_user_premium(user_id)
        await message.answer(
            "🔥💀 <b>ПОЗДРАВЛЯЮ! Премиум Sadix MS успешно активирован!</b> 💎\n\n"
            "😈 Теперь тебе доступны <b>БЕСКОНЕЧНЫЕ СКАЧИВАНИЯ 24/7</b> без каких-либо лимитов!\n"
            "Отправляй ссылки на любые видео в любое время! 🔥",
            reply_markup=get_main_keyboard(True)
        )
    else:
        await message.answer(
            "❌ <b>Неверный секретный ключ премиума!</b>\n\n"
            "Используй правильную команду активации:\n"
            "👉 <code>/premium Sadixll</code>"
        )

@dp.callback_query(F.data == "buy_premium")
async def cb_premium(callback: types.CallbackQuery):
    await callback.message.answer(
        "💎 <b>АКТИВАЦИЯ ПРЕМИУМ SADIX MS:</b>\n\n"
        "Отправь команду:\n"
        "👉 <code>/premium Sadixll</code>"
    )
    await callback.answer()

@dp.callback_query(F.data == "check_status")
async def cb_status(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await database.get_or_create_user(user_id, callback.from_user.username, callback.from_user.first_name)
    is_prem = bool(user["is_premium"])
    rem = max(0, FREE_DAILY_LIMIT - user["downloads_today"])
    status_label = "🔥 ПРЕМИУМ" if is_prem else f"⚡ БЕСПЛАТНЫЙ ({rem}/{FREE_DAILY_LIMIT} осталось)"
    
    await callback.message.answer(
        f"💀 <b>СТАТИСТИКА SADIX MS:</b>\n\n"
        f"👑 Статус: <b>{status_label}</b>\n"
        f"📥 Сегодня: <b>{user['downloads_today']}</b>\n"
        f"🏆 Всего: <b>{user['total_downloads']}</b>"
    )
    await callback.answer()

@dp.callback_query(F.data == "supported_sites")
async def cb_supported(callback: types.CallbackQuery):
    await callback.message.answer(
        "💀 <b>ПОДДЕРЖИВАЕМЫЕ ПЛАТФОРМЫ:</b>\n\n"
        "🎬 YouTube (Shorts & видео)\n"
        "🎵 TikTok (без водяных знаков)\n"
        "📸 Instagram (Reels, видео)\n"
        "🐦 Twitter / X, VK, Facebook, Reddit, Pinterest и ещё 1000+ сайтов!"
    )
    await callback.answer()

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    text = message.text.strip()
    
    match = URL_REGEX.search(text)
    if not match:
        await message.answer("😈 Отправь мне ссылку на видео или нажми /start")
        return
        
    url = match.group(0)
    can_download, remaining, is_prem = await database.check_download_limit(user_id, username, message.from_user.first_name)
    
    if not can_download:
        await message.answer("🚫 Лимит исчерпан! Бесплатно 5 видео в день. Активируй премиум: /premium Sadixll")
        return
        
    status_msg = await message.answer("😈 <b>[Sadix MS]</b> Ссылка принята! Захватываю видео из соцсети... 🔥")
    res = await download_video(url)
    
    if not res.get("success"):
        err = res.get("error", "Ошибка загрузки.")
        await database.record_failed_download(user_id, username, url, err)
        await status_msg.edit_text(f"💀 <b>[Sadix MS] Ошибка:</b>\n{err}")
        return
        
    filepath = res.get("filepath")
    title = res.get("title", "Видео")
    
    try:
        await status_msg.edit_text("😈 <b>[Sadix MS]</b> Видео загружено! Отправляю в Telegram... 🚀")
        await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
        
        caption = f"😈 <b>[Sadix MS]</b> Загрузка завершена! 🔥\n🎬 <b>{title[:100]}</b>\n💎 <i>Скачано через Sadix MS Downloader</i>"
        await message.reply_video(
            video=FSInputFile(filepath),
            caption=caption,
            duration=int(res.get("duration") or 0) or None,
            supports_streaming=True
        )
        await database.record_successful_download(user_id, username, url, title)
        try:
            await status_msg.delete()
        except Exception:
            pass
    except Exception as e:
        await database.record_failed_download(user_id, username, url, str(e))
        await message.answer(f"💀 Ошибка отправки: {str(e)}")
    finally:
        cleanup_file(filepath)

async def health_check_handler(request):
    return web.Response(text="😈 Sadix MS Downloader is RUNNING 24/7! 🔥")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    database.init_db()
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
