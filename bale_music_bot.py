"""
bale_music_bot.py  (REFACTORED for Balethon)
"""

from __future__ import annotations

import os
import re
import sys
import asyncio
import logging
import tempfile
from pathlib import Path

from balethon import Client                # Balethon's main client class
from balethon.conditions import private    # Optional: only respond in private chats
from youtube_downloader import download_audio

# ── Configuration ─────────────────────────────────────────────────────────
TOKEN = os.getenv("BALE_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bale_bot")

# YouTube URL regex pattern
YT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+",
    re.IGNORECASE,
)

bot = Client(token=TOKEN)


# ── Event Handlers ───────────────────────────────────────────────────────
@bot.on_message()
async def on_message(message):
    """Handle all incoming text messages."""
    if not message.text:
        return

    text = message.text.strip()
    chat_id = message.chat.id

    # ── Command handlers ───────────────────────────────────────────────
    if text == "/start":
        await bot.send_message(
            chat_id,
            "🎵 **Bale YouTube Music Bot**\n\n"
            "Send me a YouTube link and I'll download the audio as **MP3 320 kbps**.\n\n"
            "🌐 _avasam.ir_"
        )
        return

    if text == "/help":
        await bot.send_message(
            chat_id,
            "📌 **Usage:**\n"
            "Just send a YouTube URL, e.g.:\n"
            "`https://youtu.be/dQw4w9WgXcQ`\n\n"
            "⚡ The bot downloads the best audio and sends it as an MP3 file."
        )
        return

    # ── YouTube URL handling ───────────────────────────────────────────
    urls = YT_RE.findall(text)
    for url in urls:
        asyncio.create_task(_handle_download(chat_id, url))


async def _handle_download(chat_id: int, url: str):
    """Download audio with semaphore-based concurrency control."""
    async with DOWNLOAD_SEMAPHORE:
        # Send a temporary status message
        status_msg = await bot.send_message(
            chat_id,
            f"⏳ **Processing…**\n`{url[:60]}…`"
        )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Run the blocking download_audio in a thread pool
                loop = asyncio.get_running_loop()
                mp3_path = await loop.run_in_executor(
                    None, download_audio, url, tmpdir
                )

                if mp3_path is None:
                    await bot.edit_message_text(
                        chat_id,
                        status_msg.id,
                        "❌ **Download failed** — all 8 methods exhausted.\n"
                        "The video may be geo‑blocked or YouTube may have rate‑limited this IP.\n"
                        "Try again in a few minutes."
                    )
                    return

                file_size_mb = mp3_path.stat().st_size / (1024 * 1024)

                # Update the status message to show upload progress
                await bot.edit_message_text(
                    chat_id,
                    status_msg.id,
                    f"📤 **Uploading…** ({file_size_mb:.1f} MB)"
                )

                # Send the MP3 file as a document
                await bot.send_document(
                    chat_id,
                    mp3_path,   # Balethon accepts a file path directly
                    caption=f"🎧 {mp3_path.stem}\n🔊 MP3 320 kbps | {file_size_mb:.1f} MB",
                )

                # Clean up the temporary status message
                await bot.delete_message(chat_id, status_msg.id)

        except Exception as exc:
            logger.exception("Download task failed")
            try:
                await bot.edit_message_text(
                    chat_id,
                    status_msg.id,
                    f"⚠️ **Error:** {exc}"
                )
            except Exception:
                pass


if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Set BALE_BOT_TOKEN environment variable!")
        sys.exit(1)
    bot.run()
