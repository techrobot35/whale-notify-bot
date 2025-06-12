import json
import telebot
from web3 import Web3
import time
import threading
import logging

# ✅ Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🛠 Telegram Bot API Token
API_TOKEN = "7509126650:AAGVflMe266qvYBTAtqAEcg51iq9HTKAfHI"
bot = telebot.TeleBot(API_TOKEN)

# 📄 JSON Database File
DB_FILE = "wallets.json"

# ⛓ Blockchain RPC URLs
BSC_RPC = "https://bsc-dataseed.binance.org/"
web3 = Web3(Web3.HTTPProvider(BSC_RPC))

# 🔄 Load or Create Wallet Database
def load_wallets():
    try:
        with open(DB_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_wallets(wallets):
    with open(DB_FILE, "w") as file:
        json.dump(wallets, file, indent=4)

wallets = load_wallets()

# 📌 Main Menu
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("➕ Add Wallet", "📜 View Wallets")
    markup.row("🗑 Remove Wallet")
    return markup

# 🏠 Start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 Welcome to Whale Notify!\nManage your wallets below.", reply_markup=main_menu())

# ➕ Add Wallet
@bot.message_handler(func=lambda message: message.text == "➕ Add Wallet")
def ask_wallet_address(message):
    bot.send_message(message.chat.id, "📩 Please send your **wallet address**:")
    bot.register_next_step_handler(message, save_wallet)

def save_wallet(message):
    address = message.text.strip()
    if not Web3.is_address(address):
        bot.send_message(message.chat.id, "❌ Invalid wallet address! Please try again.")
        return
    bot.send_message(message.chat.id, "📝 Would you like to add a **name** for this wallet? (Optional)")
    bot.register_next_step_handler(message, lambda msg: save_wallet_with_name(msg, address))

def save_wallet_with_name(message, address):
    user_id = str(message.chat.id)
    name = message.text.strip()
    
    if user_id not in wallets:
        wallets[user_id] = []
    
    wallets[user_id].append({"address": address, "name": name if name else "Unnamed", "last_balance": web3.eth.get_balance(address)})
    save_wallets(wallets)
    
    bot.send_message(message.chat.id, f"✅ Wallet **{address}** added successfully!", reply_markup=main_menu())

# 📜 View Wallets
@bot.message_handler(func=lambda message: message.text == "📜 View Wallets")
def show_wallets(message):
    user_id = str(message.chat.id)
    if user_id not in wallets or not wallets[user_id]:
        bot.send_message(message.chat.id, "❌ No wallets found! Please add one.")
        return
    
    wallet_list = "\n".join([f"🔹 {w['name']} - `{w['address']}`" for w in wallets[user_id]])
    bot.send_message(message.chat.id, f"📜 **Your Wallets:**\n{wallet_list}", parse_mode="Markdown")

# 🗑 Remove Wallet
@bot.message_handler(func=lambda message: message.text == "🗑 Remove Wallet")
def ask_remove_wallet(message):
    user_id = str(message.chat.id)
    if user_id not in wallets or not wallets[user_id]:
        bot.send_message(message.chat.id, "❌ No wallets found to remove!")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for wallet in wallets[user_id]:
        markup.add(wallet["name"])
    
    bot.send_message(message.chat.id, "🗑 Select the wallet to remove:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_remove_wallet)

def confirm_remove_wallet(message):
    user_id = str(message.chat.id)
    selected_wallet = message.text.strip()
    
    for wallet in wallets[user_id]:
        if wallet["name"] == selected_wallet:
            bot.send_message(message.chat.id, f"⚠️ Are you sure you want to remove **{wallet['name']}**?\nReply with 'Yes' or 'No'.")
            bot.register_next_step_handler(message, lambda msg: delete_wallet(msg, wallet, user_id))
            return
    
    bot.send_message(message.chat.id, "❌ Wallet not found! Please try again.")

def delete_wallet(message, wallet, user_id):
    if message.text.lower() != "yes":
        bot.send_message(message.chat.id, "❌ Wallet removal cancelled!", reply_markup=main_menu())
        return
    
    wallets[user_id] = [w for w in wallets[user_id] if w != wallet]
    save_wallets(wallets)
    bot.send_message(message.chat.id, f"✅ Wallet **{wallet['name']}** removed successfully!", reply_markup=main_menu())

# 🔄 Monitor Transactions (Optimized)
def monitor_wallets():
    while True:
        wallets = load_wallets()  # Reload updated wallets from database
        for user_id, user_wallets in wallets.items():
            for wallet in user_wallets:
                address = wallet["address"]
                new_balance = web3.eth.get_balance(address)

                if "last_balance" in wallet and wallet["last_balance"] != new_balance:
                    difference = new_balance - wallet["last_balance"]
                    action = "Received" if difference > 0 else "Sent"
                    bot.send_message(user_id, f"🚨 **Transaction Alert!**\n{action} `{abs(difference) / 10**18:.6f} BNB` in `{address}`", parse_mode="Markdown")

                wallet["last_balance"] = new_balance  # Update balance
        save_wallets(wallets)  # Save updated balances
        time.sleep(30)  # ⏳ Check every 30 seconds

# 🏃 Run Background Monitoring with Threading
threading.Thread(target=monitor_wallets, daemon=True).start()

# 🚀 Start Bot
logging.info("🚀 Bot is running...")
bot.polling(none_stop=True)
