from flask import Flask, request, jsonify
from pyrogram import Client, filters
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['anime_database']
collection = db['posts']

# Pyrogram client setup
api_id = 'YOUR_API_ID'
api_hash = 'YOUR_API_HASH'
bot_token = 'YOUR_BOT_TOKEN'

bot = Client('my_bot', api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Home route
@app.route('/')
def home():
    return "Welcome to Pro Anime Auto-Poster Bot!"

# Command to start the bot
@bot.on_message(filters.command('start'))
def start(client, message):
    client.send_message(message.chat.id, 'Welcome to Pro Anime Auto-Poster!')

# Callback handler for posting
@bot.on_message(filters.command('post'))
def post(client, message):
    # Implementation for posting
    data = request.get_json()
    collection.insert_one(data)
    client.send_message(message.chat.id, 'Post created!')

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    bot.process_new_updates([Client.update(update)])
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=5000)
    bot.run()