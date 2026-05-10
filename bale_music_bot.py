"""
bale_music_bot.py  (FIXED: imports handler, not handlers)
"""

from __future__ import annotations

import os
import re
import sys
import asyncio
import logging
import tempfile
from pathlib import Path

from bale import Bot, Message, InputFile
from bale.handler import MessageHandler          # ← corrected import

from youtube_downloader import download_audio

# ── Config ───────────────────────────────────────────────────────────────
TOKEN = os.getenv("BALE_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bale_bot")

YT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+",
    re.IGNORECASE,
)

bot = Bot(token=TOKEN)

# ── Handlers ─────────────────────────────────────────────────────────────

@bot.listen("on_ready")
async def on_ready():
    await bot.delete_webhook()
    logger.info("🤖 Bot is ready — %s", bot.user)


@bot.listen("on_message")
async def on_message(message: Message):
    if not message.content:
        return

    text = message.content.strip()
    chat = message.chat

    if text == "/start":
        await chat.send(
            "🎵 **Bale YouTube Music Bot**\n\n"
            "Send me a YouTube link and I'll download the audio as **MP3 320 kbps**.\n\n"
            "🌐 _avasam.ir_"
        )
        return

    if text == "/help":
        await chat.send(
            "📌 **Usage:**\n"
            "Just send a YouTube URL, e.g.:\n"
            "`https://youtu.be/dQw4w9WgXcQ`\n\n"
            "⚡ The bot downloads the best audio and sends it as an MP3 file."
        )
        return

    urls = YT_RE.findall(text)
    for url in urls:
        asyncio.create_task(_handle_download(chat, url))


async def _handle_download(chat, url: str):
    async with DOWNLOAD_SEMAPHORE:
        status_msg = await chat.send(f"⏳ **Processing…**\n`{url[:60]}…`")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                loop = asyncio.get_running_loop()
                mp3_path = await loop.run_in_executor(
                    None, download_audio, url, tmpdir
                )

                if mp3_path is None:
                    await status_msg.edit(
                        "❌ **Download failed** — all 8 methods exhausted.\n"
                        "The video may be geo‑blocked or YouTube may have rate‑limited this IP.\n"
                        "Try again in a few minutes."
                    )
                    return

                file_size_mb = mp3_path.stat().st_size / (1024 * 1024)

                await status_msg.edit(f"📤 **Uploading…** ({file_size_mb:.1f} MB)")

                with open(mp3_path, "rb") as fh:
                    file_bytes = fh.read()

                await chat.send_document(
                    document=InputFile(file_bytes, file_name=mp3_path.name),
                    caption=f"🎧 {mp3_path.stem}\n🔊 MP3 320 kbps | {file_size_mb:.1f} MB",
                )

                await status_msg.delete()

        except Exception as exc:
            logger.exception("Download task failed")
            try:
                await status_msg.edit(f"⚠️ **Error:** {exc}")
            except Exception:
                pass


if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Set BALE_BOT_TOKEN environment variable!")
        sys.exit(1)
    bot.run()
