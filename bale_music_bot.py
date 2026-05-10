import os
import yt_dlp
from balethon import Client
from balethon.conditions import regex

# Replace with your actual bot token from BotFather in Bale
BOT_TOKEN = "1011430416:5JY8CU9nGwYtVz0ahfDEIkJyCkVTUCAhLXQ"
bot = Client(BOT_TOKEN)

# Listen for messages containing a SoundCloud URL
@bot.on_message(regex(r"(https?://(?:www\.)?soundcloud\.com/\S+)"))
async def handle_soundcloud_link(message):
    url = message.matches[0]
    reply_msg = await message.reply("⏳ Downloading your track, please wait...")

    # yt-dlp configuration for audio extraction
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s', # Saves file in the current directory temporarily
        'noplaylist': True,             # Only download a single track, not playlists
        'quiet': True
    }

    try:
        # Download the audio using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)

        # Send the downloaded audio file back to the user
        await bot.send_audio(message.chat.id,filename, caption=info_dict.get('title', 'Downloaded Track'))
        
        # Clean up the file from the server after sending
        if os.path.exists(filename):
            os.remove(filename)
            
        await reply_msg.edit_text("✅ Download complete!")

    except Exception as e:
        await reply_msg.edit_text(f"❌ An error occurred: {str(e)}")

@bot.on_message()
async def welcome(message):
    await bot.send_message(message.chat.id,"Send me a SoundCloud link and I will download it for you!")

if __name__ == "__main__":
    print("Bot is running...")
    bot.run()
