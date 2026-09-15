import os
import base64
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, PREMIUM_CODE, FREE_LIMIT
from database import init_db, get_user, increment_count, set_premium
from downloader import download_video, cleanup_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sadix_ms")

# ====== COOKIES ИЗ ENV (base64) ======
cookies_b64 = os.environ.get("YOUTUBE_COOKIES")
if cookies_b64:
    try:
        with open("cookies.txt", "wb") as f:
            f.write(base64.b64decode(cookies_b64))
        logger.info("✅ Cookies загружены из ENV")
    except Exception as e:
        logger.error(f"❌ Ошибка cookies: {e}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Активировать премиум", callback_data="premium_info")
    kb.button(text="📊 Мой статус", callback_data="status")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(CommandStart())
async def start_cmd(message: Message):
    user = get_user(message.from_user.id)
    status = (
        "💎 Премиум — бесконечные скачивания"
        if user["premium"]
        else f"🆓 Бесплатно — {FREE_LIMIT - user['count']} из {FREE_LIMIT} видео сегодня"
    )
    text = (
        "😈 **Привет! Я Sadix MS** — твой личный загрузчик видео!\n\n"
        "🎬 **Скачиваю из:**\n"
        "• YouTube\n• TikTok\n• Instagram\n• Twitter/X\n• Facebook\n• VK\n\n"
        "🔓 Работаю даже с защищёнными видео\n\n"
        f"📊 **Твой статус:** {status}\n\n"
        "📥 **Просто отправь мне ссылку на видео**\n\n"
        "💎 **Премиум:** `/premium Sadixll`\n\n"
        "😈 Ворм на связи!"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard())


@dp.message(F.text.startswith("/premium"))
async def premium_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Напиши: `/premium Sadixll`", parse_mode="Markdown")
        return
    code = args[1].strip()
    if code == PREMIUM_CODE:
        set_premium(message.from_user.id)
        await message.answer(
            "💎 **Премиум активирован!**\n\n"
            "Теперь ты можешь качать **бесконечное количество видео**. 😈🔥",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Неверный премиум-код.", parse_mode="Markdown")


@dp.message(F.text == "/status")
async def status_cmd(message: Message):
    user = get_user(message.from_user.id)
    if user["premium"]:
        text = "💎 **Премиум активен**\nБесконечные скачивания 😈"
    else:
        left = FREE_LIMIT - user["count"]
        text = f"🆓 **Бесплатный тариф**\nОсталось: **{left}** из {FREE_LIMIT} видео сегодня"
    await message.answer(text, parse_mode="Markdown")


@dp.callback_query(F.data == "premium_info")
async def premium_info(cb):
    await cb.message.answer(
        "💎 **Премиум — бесконечные скачивания**\n\n"
        "Активация: `/premium Sadixll`",
        parse_mode="Markdown"
    )
    await cb.answer()


@dp.callback_query(F.data == "status")
async def status_cb(cb):
    user = get_user(cb.from_user.id)
    if user["premium"]:
        text = "💎 Премиум активен"
    else:
        left = FREE_LIMIT - user["count"]
        text = f"🆓 Осталось: {left} из {FREE_LIMIT} видео сегодня"
    await cb.message.answer(text)
    await cb.answer()


@dp.message(F.text.startswith("http"))
async def download_handler(message: Message):
    user = get_user(message.from_user.id)
    url = message.text.strip()

    if not user["premium"] and user["count"] >= FREE_LIMIT:
        await message.answer(
            "🚫 **Лимит исчерпан!**\n\n"
            f"🆓 Бесплатно — только {FREE_LIMIT} видео в день.\n"
            "💎 Активируй премиум: `/premium Sadixll`",
            parse_mode="Markdown"
        )
        return

    msg = await message.answer("⏳ Скачиваю видео...")
    result = await download_video(url)

    if not result["success"]:
        await msg.edit_text(f"😈 **Ошибка:**\n`{result['error']}`", parse_mode="Markdown")
        return

    try:
        await msg.edit_text("📤 Отправляю видео...")
        video = FSInputFile(result["filepath"])
        caption = (
            f"😈 **Sadix MS**\n"
            f"📎 {result['title'][:100]}\n"
            f"⏱ {result.get('duration', 0)} сек"
        )
        await message.answer_video(video, caption=caption, parse_mode="Markdown")
        increment_count(message.from_user.id)
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка отправки: `{str(e)[:200]}`", parse_mode="Markdown")
    finally:
        cleanup_file(result.get("filepath"))
        try:
            await msg.delete()
        except Exception:
            pass


async def main():
    init_db()
    logger.info("😈 Sadix MS бот запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
