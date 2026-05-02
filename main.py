
"""
╔══════════════════════════════════════════════════════════╗
║         Pro Anime Auto-Poster Bot - Advanced v2.0        ║
║         Fixed + Advanced | HuggingFace Ready            ║
╚══════════════════════════════════════════════════════════╝
"""

import os 
import asyncio
import requests
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
from pyrogram.errors import ChatAdminRequired, ChannelInvalid, PeerIdInvalid
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from datetime import datetime

# ═══════════════════════════════════════════
#              WEB SERVER (HuggingFace)
# ═══════════════════════════════════════════
web_app = Flask(__name__)  # <--- 'name' ko '__name__' se replace kiya


@web_app.route('/')
def home():
    return "✅ Pro Anime Bot is Online!"

def run_flask():
    web_app.run(host="0.0.0.0", port=7860)

# ═══════════════════════════════════════════
#                   CONFIG
# ═══════════════════════════════════════════
API_ID       = int(os.getenv("API_ID", "12345"))
API_HASH     = os.getenv("API_HASH", "your_hash")
BOT_TOKEN    = os.getenv("BOT_TOKEN", "your_token")
MONGO_URL    = os.getenv("MONGO_URL", "your_mongodb_url")
OWNER_ID     = int(os.getenv("OWNER_ID", "0"))  # Apna Telegram User ID daalo
SHORTENER_API = os.getenv("SHORTENER_API", "bd581438aef6ae768394f9d9ed1d1fc2c37b5f0f")

# ═══════════════════════════════════════════
#                MONGODB SETUP
# ═══════════════════════════════════════════
mongo_client = MongoClient(MONGO_URL)
db           = mongo_client["AnimeBotDB"]
channels_col = db["channels"]
settings_col = db["settings"]
stats_col    = db["stats"]
users_col    = db["users"]

# ═══════════════════════════════════════════
#              PYROGRAM CLIENT
# ═══════════════════════════════════════════
app = Client(
    "ProAnimeBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ═══════════════════════════════════════════
#           IN-MEMORY POST CACHE
#  (Callback data 64-byte limit workaround)
# ═══════════════════════════════════════════
post_cache = {}  # { "cache_key": {"title": ..., "short_link": ..., "caption": ...} }

# ═══════════════════════════════════════════
#                  HELPERS
# ═══════════════════════════════════════════

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def get_db_settings() -> dict:
    data = settings_col.find_one({"id": "bot_settings"})
    if not data:
        default = {
            "id": "bot_settings",
            "format": (
                "🥵 {title} 🍑\n"
                "╭───────────────────\n"
                "├ Powered by - @HentaiVerse_Og\n"
                "├ 🌟 Ratings - 8.9 IMDB\n"
                "├ 🔊 Audio - Hindi Dubbed\n"
                "├ 📷 Quality - Multi\n"
                "├ 🎭 Genres - H€ntai, Romance\n"
                "├───────────────────\n"
                "├ 😍 [Watch & Download 😏]({mainlink})\n"
                "╰───────────────────\n"
                "HOW TO DOWNLOAD 👇"
            )
        }
        settings_col.insert_one(default)
        return default
    return data

def get_short_link(long_url: str) -> str:
    api_url = f"https://arolinks.com/api?api={SHORTENER_API}&url={long_url}"
    try:
        res = requests.get(api_url, timeout=10).json()
        return res.get("shortenedUrl", long_url)
    except Exception:
        return long_url

def save_user(user_id: int, username: str):
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "last_seen": datetime.now()}},
        upsert=True
    )

def increment_stat(key: str):
    stats_col.update_one(
        {"id": "global"},
        {"$inc": {key: 1}},
        upsert=True
    )

def make_cache_key(title: str, short_link: str) -> str:
    """Short unique key for callback data (stays under 64 bytes)."""
    import hashlib
    raw = f"{title}|{short_link}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

# ═══════════════════════════════════════════
#           OWNER-ONLY FILTER
# ═══════════════════════════════════════════
def owner_filter(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id == OWNER_ID

owner_only = filters.create(owner_filter)

# ═══════════════════════════════════════════
#                  COMMANDS
# ═══════════════════════════════════════════

# /start
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    save_user(message.from_user.id, message.from_user.username or "")
    increment_stat("total_users")
    await message.reply_text(
        "🔥 Pro Anime Auto-Poster Bot v2.0\n\n"
        "Bina mehnat ke professional posts generate aur channels pe post karo!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ Owner Commands:\n"
        "• /addchannel — Channel link karo\n"
        "• /removechannel — Channel remove karo\n"
        "• /mychannels — Saved channels list\n"
        "• /set_format — Post template badlo\n"
        "• /get_format — Current format dekho\n"
        "• /reset_format — Format reset karo\n"
        "• /stats — Bot stats dekho\n\n"
        "📝 Post Banao:\n"
        "• /anime Title | Link — Single post\n"
        "• /bulkpost — Bulk posts (file se)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 _Bot by @HentaiVerse_Og_",
        disable_web_page_preview=True
    )


# /addchannel
@app.on_message(filters.command("addchannel") & filters.private & owner_only)
async def add_channel_cmd(client: Client, message: Message):
    await message.reply_text(
        "📢 Channel Link Karne Ka Tarika:\n\n"
        "Us channel se koi bhi message yahan forward karo.\n"
        "_(Bot ko us channel mein Admin hona zaruri hai)_"
    )


# Handle forwarded messages to detect channel
@app.on_message(filters.forwarded & filters.private & owner_only)
async def handle_forward(client: Client, message: Message):
    try:
        # Pyrogram v2 uses forward_origin
        origin = message.forward_origin
        if origin and hasattr(origin, "chat"):
            chat = origin.chat
            chat_id    = chat.id
            chat_title = chat.title or "Unknown"
        elif message.forward_from_chat:
            # fallback for older versions
            chat_id    = message.forward_from_chat.id
            chat_title = message.forward_from_chat.title or "Unknown"
        else:
            return await message.reply_text("❌ Yeh message kisi channel se forward nahi hai.")

        channels_col.update_one(
            {"chat_id": chat_id},
            {"$set": {"name": chat_title, "added_on": datetime.now()}},
            upsert=True
        )
        await message.reply_text(f"✅ Channel Linked!\n📛 Name: {chat_title}\n🆔 ID: {chat_id}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# /removechannel
@app.on_message(filters.command("removechannel") & filters.private & owner_only)
async def remove_channel_cmd(client: Client, message: Message):
    channels = list(channels_col.find())
    if not channels:
        return await message.reply_text("❌ Koi channel saved nahi hai.")

    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"🗑 {ch['name']}",
                callback_data=f"rmch|{ch['chat_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    await message.reply_text(
        "🗑 Konsa channel remove karna hai?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^rmch\|"))
async def cb_remove_channel(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)
    _, chat_id = cq.data.split("|")
    channels_col.delete_one({"chat_id": int(chat_id)})
    await cq.message.edit_text("✅ Channel remove kar diya gaya!")

# /mychannels
@app.on_message(filters.command("mychannels") & filters.private & owner_only)
async def my_channels(client: Client, message: Message):
    channels = list(channels_col.find())
    if not channels:
        return await message.reply_text("❌ Koi channel linked nahi hai.\n/addchannel se channel add karo.")

    text = "📋 Linked Channels:\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch['name']}\n   🆔 {ch['chat_id']}\n\n"
    await message.reply_text(text)


# /set_format
@app.on_message(filters.command("set_format") & filters.private & owner_only)
async def set_format_cmd(client: Client, message: Message):
    args = message.text.split("/set_format", 1)
    if len(args) < 2 or not args[1].strip():
        return await message.reply_text(
            "📝 Format kaise set karein:\n\n"
            "/set_format aapka format yahan\n\n"
            "Variables:\n"
            "• {title} — Anime title\n"
            "• {mainlink} — Short download link\n\n"
            "Example:\n"
            "/set_format 🎬 {title}\n[Download]({mainlink})"
        )
    new_format = args[1].strip()
    settings_col.update_one(
        {"id": "bot_settings"},
        {"$set": {"format": new_format}},
        upsert=True
    )
    await message.reply_text(
        f"✅ Format update ho gaya!\n\nPreview:\n\n"
        + new_format.replace("{title}", "Test Anime").replace("{mainlink}", "https://example.com"),
        disable_web_page_preview=True
    )


# /get_format
@app.on_message(filters.command("get_format") & filters.private & owner_only)
async def get_format_cmd(client: Client, message: Message):
    s = get_db_settings()
    await message.reply_text(
        f"📋 Current Format:\n\n{s['format']}"
    )


# /reset_format
@app.on_message(filters.command("reset_format") & filters.private & owner_only)
async def reset_format_cmd(client: Client, message: Message):
    settings_col.delete_one({"id": "bot_settings"})
    get_db_settings()  # recreates default
    await message.reply_text("✅ Format default par reset ho gaya!")


# /stats
@app.on_message(filters.command("stats") & filters.private & owner_only)
async def stats_cmd(client: Client, message: Message):
    s = stats_col.find_one({"id": "global"}) or {}
    total_users    = users_col.count_documents({})
    total_channels = channels_col.count_documents({})
    posts_created  = s.get("posts_created", 0)
    posts_sent     = s.get("posts_sent", 0)

    await message.reply_text(
        "📊 Bot Statistics:\n\n"
        f"👤 Total Users: {total_users}\n"
        f"📢 Linked Channels: {total_channels}\n"
        f"📝 Posts Created: {posts_created}\n"
        f"🚀 Posts Sent: {posts_sent}\n\n"
        f"🟢 Status: Online"
    )


# /anime Title | Link   ← Main post creator
@app.on_message(filters.command("anime") & filters.private & owner_only)
async def create_post(client: Client, message: Message):
    text = message.text.split("/anime", 1)
    if len(text) < 2 or "|" not in text[1]:
        return await message.reply_text(
            "❌ Galat format!\n\n"
            "✅ Sahi format:\n/anime Title | Link\n\n"
            "Example:\n/anime Boku No Pico | https://example.com/ep1"
        )

    channels = list(channels_col.find())
    if not channels:
        return await message.reply_text("❌ Pehle /addchannel karein aur channel link karein.")

    parts      = text[1].split("|", 1)
    title      = parts[0].strip()
    long_url   = parts[1].strip()

    status_msg = await message.reply_text("⏳ Short link bana raha hoon...")
    short_link = get_short_link(long_url)
    increment_stat("posts_created")

    current_settings = get_db_settings()
    caption = (
        current_settings["format"]
        .replace("{title}", title)
        .replace("{mainlink}", short_link)
    )

# Cache the post data (solves 64-byte callback data limit)
    cache_key = make_cache_key(title, short_link)
    post_cache[cache_key] = {
        "title":      title,
        "short_link": short_link,
        "caption":    caption
    }

    # Build channel buttons
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"📤 Post to: {ch['name']}",
                callback_data=f"send|{cache_key}|{ch['chat_id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("📤 Post to ALL Channels", callback_data=f"sendall|{cache_key}"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ])

    await status_msg.edit_text(
        f"📝 Post Preview:\n\n{caption}\n\n"
        f"🔗 Short Link: {short_link}\n\n"
        "👇 Channel chunein jahan post karna hai:",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )


# Callback: Send to specific channel
@app.on_callback_query(filters.regex(r"^send\|"))
async def cb_send_to_channel(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)

    parts      = cq.data.split("|")  # ["send", cache_key, chat_id]
    cache_key  = parts[1]
    chat_id    = int(parts[2])

    cached = post_cache.get(cache_key)
    if not cached:
        return await cq.answer("❌ Post cache expire ho gaya. Dobara /anime karein.", show_alert=True)

    short_link = cached["short_link"]
    caption    = cached["caption"]

    btns = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 𝗧𝗨𝗧𝗢𝗥𝗜𝗔𝗟 🎬",   url="https://t.me/Hentai_Dekhobot?start=BQADAQADZxgAAlQyqEbZtQPk2rwcpBYE"),
            InlineKeyboardButton("🛡️ 𝗕𝗔𝗖𝗞-𝗨𝗣 🛡️",    url="https://t.me/+u4Uxe7F97UZlNzI1")
        ],
        [InlineKeyboardButton("📥 𝗪𝗔𝗧𝗖𝗛 & 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 📥", url=short_link)]
    ])

    try:
        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=btns,
            disable_web_page_preview=True
        )
        increment_stat("posts_sent")
        await cq.answer("🚀 Post ho gaya!", show_alert=True)
    except ChatAdminRequired:
        await cq.answer("❌ Bot ko Admin banao us channel mein!", show_alert=True)
    except (ChannelInvalid, PeerIdInvalid):
        await cq.answer("❌ Channel invalid hai. Remove karke dobara add karo.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ Error: {e}", show_alert=True)


# Callback: Send to ALL channels
@app.on_callback_query(filters.regex(r"^sendall\|"))
async def cb_send_to_all(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)

    cache_key = cq.data.split("|")[1]
    cached = post_cache.get(cache_key)
    if not cached:
        return await cq.answer("❌ Cache expire. Dobara /anime karein.", show_alert=True)

    channels   = list(channels_col.find())
    short_link = cached["short_link"]
    caption    = cached["caption"]

    btns = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 𝗧𝗨𝗧𝗢𝗥𝗜𝗔𝗟 🎬",   url="https://t.me/Hentai_Dekhobot?start=BQADAQADZxgAAlQyqEbZtQPk2rwcpBYE"),
            InlineKeyboardButton("🛡️ 𝗕𝗔𝗖𝗞-𝗨𝗣 🛡️",    url="https://t.me/+u4Uxe7F97UZlNzI1")
        ],
        [InlineKeyboardButton("📥 𝗪𝗔𝗧𝗖𝗛 & 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 📥", url=short_link)]
    ])

             # ... previous code inside the function ...
    success, failed = 0, 0
    for ch in channels:
        try:
            await client.send_message(...)
            success += 1
            # ... rest of your loop ...
        except Exception:
            failed += 1
    
    # INDENT THESE LINES BELOW:
    await cq.message.edit_text(
        f"✅ Bulk Post Complete!\n\n"
        f"✅ Success: {success} channels\n"
        f"❌ Failed: {failed} channels"
    )




# /bulkpost — Multiple animes ek saath
@app.on_message(filters.command("bulkpost") & filters.private & owner_only)
async def bulk_post_help(client: Client, message: Message):
    await message.reply_text(
        "📦 Bulk Post Format:\n\n"
        "Har line mein ek entry:\n"
        "Title1 | Link1\n"
        "Title2 | Link2\n"
        "Title3 | Link3\n\n"
        "Aur command aisa use karo:\n"
        "/bulk\n"
        "Title1 | Link1\n"
        "Title2 | Link2"
    )


@app.on_message(filters.command("bulk") & filters.private & owner_only)
async def bulk_post_cmd(client: Client, message: Message):
    text = message.text.split("/bulk", 1)
    if len(text) < 2 or not text[1].strip():
        return await message.reply_text("❌ Entries daalo! /bulkpost se format dekho.")

    channels = list(channels_col.find())
    if not channels:
        return await message.reply_text("❌ Pehle channel link karo.")

    lines = [l.strip() for l in text[1].strip().split("\n") if "|" in l]
    if not lines:
        return await message.reply_text("❌ Koi valid entry nahi mili. Format: Title | Link")

    status = await message.reply_text(f"⏳ {len(lines)} posts process ho rahe hain...")

    current_settings = get_db_settings()
    success_count = 0

    for line in lines:
        try:
            parts = line.split("|", 1)
            title, long_url = parts[0].strip(), parts[1].strip()
            short_link = get_short_link(long_url)
            caption = (
                current_settings["format"]
                .replace("{title}", title)
                .replace("{mainlink}", short_link)
            )
            btns = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 𝗧𝗨𝗧𝗢𝗥𝗜𝗔𝗟 🎬", url="https://t.me/Hentai_Dekhobot?start=BQADAQADZxgAAlQyqEbZtQPk2rwcpBYE"),
                    InlineKeyboardButton("🛡️ 𝗕𝗔𝗖𝗞-𝗨𝗣 🛡️",  url="https://t.me/+u4Uxe7F97UZlNzI1")
                ],
                [InlineKeyboardButton("📥 𝗪𝗔𝗧𝗖𝗛 & 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 📥", url=short_link)]
            ])
            for ch in channels:
                await client.send_message(
                    chat_id=ch["chat_id"],
                    text=caption,
                    reply_markup=btns,
                    disable_web_page_preview=True
                )
                await asyncio.sleep(1)
            increment_stat("posts_sent")
            success_count += 1
        except Exception:
            pass

    await status.edit_text(
        f"✅ Bulk Post Done!\n\n"
        f"📝 Total entries: {len(lines)}\n"
        f"✅ Posted: {success_count}\n"
        f"❌ Failed: {len(lines) - success_count}"
    )


# /broadcast — Owner se sab users ko message
@app.on_message(filters.command("broadcast") & filters.private & owner_only)
async def broadcast_cmd(client: Client, message: Message):
    text = message.text.split("/broadcast", 1)
    if len(text) < 2 or not text[1].strip():
        return await message.reply_text("❌ Message daalo: /broadcast Aapka message")

    bcast_text = text[1].strip()
    all_users  = list(users_col.find({}, {"user_id": 1}))
    status     = await message.reply_text(f"📡 Broadcasting to {len(all_users)} users...")

    done, failed = 0, 0
    for user in all_users:
        try:
            await client.send_message(chat_id=user["user_id"], text=bcast_text)
            done += 1
            await asyncio.sleep(0.1)
        except Exception:
            failed += 1

    await status.edit_text(
        f"📡 Broadcast Complete!\n\n"
        f"✅ Sent: {done}\n❌ Failed: {failed}"
    )


# Cancel button
@app.on_callback_query(filters.regex("^cancel$"))
async def cb_cancel(client: Client, cq: CallbackQuery):
    await cq.message.edit_text("❌ Cancelled.")

# ═══════════════════════════════════════════
#                  MAIN
# ═══════════════════════════════════════════
async def main():
    # Flask ko thread mein chalana zaruri hai HuggingFace ke liye
    Thread(target=run_flask, daemon=True).start()
    
    await app.start()
    print("✅ Bot started successfully!")
    await idle
