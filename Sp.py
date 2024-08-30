import telebot
from threading import Thread, Event
from Api import sms, call
from time import sleep
from inspect import getmembers, isfunction
import mysql.connector
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.asyncio_storage import StateMemoryStorage
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot_token = '7330729864:AAE1QK7hCAEFmtrpaXd9ZjMObzO864uqSo4'
bot = telebot.TeleBot(bot_token, state_storage=StateMemoryStorage())
SMS_SERVICES = [i[0] for i in getmembers(sms, isfunction)]
CALL_SERVICES = [i[0] for i in getmembers(call, isfunction)]
MAIN_CHANNEL_ID = '@ExoShopVpn'

DB_NAME = 'Exosms'
DB_HOST = 'localhost'
DB_USER = 'z0roday'
DB_PASS = 'z0roday@@123%&&&'

bombing_events = {}

def setup_database():
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT UNIQUE,
        username VARCHAR(255),
        last_use DATETIME,
        use_count INT DEFAULT 0,
        is_blocked BOOLEAN DEFAULT FALSE,
        block_until DATETIME,
        custom_limit INT DEFAULT 2
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INT AUTO_INCREMENT PRIMARY KEY,
        admin_id BIGINT UNIQUE
    )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)

def execute_db_query(query, params=None, fetch=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result

def save_user(user_id, username):
    execute_db_query('''
    INSERT INTO users (user_id, username, last_use, use_count)
    VALUES (%s, %s, NOW(), 0)
    ON DUPLICATE KEY UPDATE username = %s
    ''', (user_id, username, username))

def update_user_usage(user_id):
    execute_db_query('''
    UPDATE users 
    SET last_use = NOW(), use_count = use_count + 1
    WHERE user_id = %s
    ''', (user_id,))

def check_user_limit(user_id):
    result = execute_db_query('''
    SELECT use_count, last_use, is_blocked, block_until, custom_limit
    FROM users
    WHERE user_id = %s
    ''', (user_id,), fetch=True)
    
    if result:
        use_count, last_use, is_blocked, block_until, custom_limit = result[0]
        if is_blocked:
            if block_until and datetime.now() > block_until:
                unblock_user(user_id)
                return True
            return False
        if use_count >= custom_limit:
            if datetime.now() - last_use > timedelta(hours=24):
                reset_user_usage(user_id)
                return True
            return False
        return True
    return True

def reset_user_usage(user_id):
    execute_db_query('''
    UPDATE users 
    SET use_count = 0, last_use = NOW()
    WHERE user_id = %s
    ''', (user_id,))

def ban_user(user_id, duration_minutes):
    block_until = datetime.now() + timedelta(minutes=duration_minutes)
    execute_db_query('''
    UPDATE users 
    SET is_blocked = TRUE, block_until = %s
    WHERE user_id = %s
    ''', (block_until, user_id))

def unban_user(user_id):
    execute_db_query('''
    UPDATE users 
    SET is_blocked = FALSE, block_until = NULL
    WHERE user_id = %s
    ''', (user_id,))

def is_admin(user_id):
    result = execute_db_query('SELECT * FROM admins WHERE admin_id = %s', (user_id,), fetch=True)
    return bool(result)

def add_admin(admin_id):
    execute_db_query('INSERT IGNORE INTO admins (admin_id) VALUES (%s)', (admin_id,))

def set_custom_limit(user_id, limit):
    execute_db_query('''
    UPDATE users 
    SET custom_limit = %s
    WHERE user_id = %s
    ''', (limit, user_id))


def check_membership(user_id):
    try:
        member = bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiException:
        return False

@bot.message_handler(commands=['start'])
def start(message):
    if check_membership(message.from_user.id):
        welcome_message = f"Welcome, {message.from_user.first_name}!"
        if is_admin(message.from_user.id):
            welcome_message += " (Admin)"
        if not check_user_limit(message.from_user.id):
            welcome_message += "\nYou have reached your usage limit"
        save_user(message.from_user.id, message.from_user.username)
        keyboard = create_keyboard(message.from_user.id)
        bot.send_message(message.chat.id, welcome_message)
        bot.send_message(message.chat.id, "Please choose an option:", reply_markup=keyboard)
    else:
        markup = InlineKeyboardMarkup()
        join_button = InlineKeyboardButton(text='Join Channel', url=f'https://t.me/{MAIN_CHANNEL_ID[1:]}')
        markup.add(join_button)
        github_button = InlineKeyboardButton(text='GitHub', url='https://github.com/z0roday')
        check_button = InlineKeyboardButton(text='Confirm Membership', callback_data='check_membership')
        markup.row(github_button, check_button)
        bot.reply_to(message, "Please join our channel first:", reply_markup=markup)

def create_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('SMS'), KeyboardButton('Support'))
    if is_admin(user_id):
        keyboard.add(KeyboardButton('Admin Panel'))
    return keyboard

def run_bot():
    while True:
        try:
            logger.info("Starting bot polling...")
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            sleep(15)

@bot.message_handler(func=lambda message: message.text == 'Admin Panel')
def handle_admin_panel(message):
    if is_admin(message.from_user.id):
        show_admin_panel(message)
    else:
        bot.reply_to(message, "You don't have permission to access the admin panel.")

@bot.message_handler(commands=['admin'])
def show_admin_panel(message):
    if is_admin(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Admin Info", callback_data="admin_info"),
                   InlineKeyboardButton("Broadcast", callback_data="broadcast"))
        markup.row(InlineKeyboardButton("Add Admin", callback_data="add_admin"),
                   InlineKeyboardButton("Ban User", callback_data="ban_user"))
        markup.row(InlineKeyboardButton("Unban User", callback_data="unban_user"),
                   InlineKeyboardButton("Set User Limit", callback_data="set_user_limit"))
        markup.row(InlineKeyboardButton("Set Global Limit", callback_data="set_global_limit"))
        markup.row(InlineKeyboardButton("Cancel", callback_data="cancel_admin"))
        bot.send_message(message.chat.id, "Admin panel:", reply_markup=markup)
    else:
        bot.reply_to(message, "You don't have permission to access the admin panel.")

@bot.callback_query_handler(func=lambda call: call.data in ["admin_info", "broadcast", "add_admin", "ban_user", "unban_user", "set_user_limit", "set_global_limit", "cancel_admin", "check_membership"])
def callback_query(call):
    if call.data in ["admin_info", "broadcast", "add_admin", "ban_user", "unban_user", "set_user_limit", "set_global_limit", "cancel_admin"]:
        if is_admin(call.from_user.id):
            if call.data == "admin_info":
                admin_info_command(call.message)
            elif call.data == "broadcast":
                bot.answer_callback_query(call.id, "Please enter the broadcast message:")
                bot.register_next_step_handler(call.message, process_broadcast)
            elif call.data == "add_admin":
                bot.answer_callback_query(call.id, "Please enter the user ID of the new admin:")
                bot.register_next_step_handler(call.message, process_new_admin)
            elif call.data == "ban_user":
                bot.answer_callback_query(call.id, "Please enter the user ID of the user you want to ban:")
                bot.register_next_step_handler(call.message, process_ban_user_id)
            elif call.data == "unban_user":
                bot.answer_callback_query(call.id, "Please enter the user ID of the user you want to unban:")
                bot.register_next_step_handler(call.message, process_unban_user_id)
            elif call.data == "set_user_limit":
                bot.answer_callback_query(call.id, "Please enter the user ID for whom you want to set a custom limit:")
                bot.register_next_step_handler(call.message, process_set_user_limit_id)
            elif call.data == "set_global_limit":
                bot.answer_callback_query(call.id, "Please enter the new global limit:")
                bot.register_next_step_handler(call.message, process_set_global_limit)
            elif call.data == "cancel_admin":
                bot.answer_callback_query(call.id, "Admin action cancelled.")
                bot.edit_message_text("Admin action cancelled.", 
                                      chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "You don't have permission to use this feature.")
    elif call.data == 'check_membership':
        if check_membership(call.from_user.id):
            bot.answer_callback_query(call.id, "Great! You've joined the channel.")
            welcome_message = f"Welcome, {call.from_user.first_name}!"
            if is_admin(call.from_user.id):
                welcome_message += " (Admin)"
            keyboard = create_keyboard(call.from_user.id)
            bot.send_message(call.message.chat.id, welcome_message)
            bot.send_message(call.message.chat.id, "Please choose an option:", reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id, "You haven't joined the channel yet. Please join and try again.")

@bot.message_handler(func=lambda message: message.text == 'SMS')
def handle_sms(message):
    bot.reply_to(message, "Please enter your Target Phone Number: ex 09000000000")
    bot.register_next_step_handler(message, get_phone)

@bot.message_handler(func=lambda message: message.text == 'Support')
def handle_support(message):
    bot.reply_to(message, "For support, please contact @z0roday")

def get_phone(message):
    if not check_membership(message.from_user.id):
        start(message)
        return
    if not check_user_limit(message.from_user.id):
        bot.reply_to(message, "You have reached your usage limit")
        return
    
    phone = message.text
    if not phone.isdigit() or len(phone) != 11:
        bot.reply_to(message, "Invalid input. Please enter a valid 11-digit phone number.")
        bot.register_next_step_handler(message, get_phone)
        return
    
    if phone in ("09938282310", "09932539709"):
        bot.send_message(message.chat.id, "Number Not Found!\n /start")
    else:
        bot.reply_to(message, "Please enter a number between 1 and 30:")
        bot.register_next_step_handler(message, get_count, phone)

def get_count(message, phone):
    if not check_membership(message.from_user.id) or not check_user_limit(message.from_user.id):
        bot.reply_to(message, "You have reached your usage limit or are not a member. Please try again later.")
        return
   
    if not message.text.isdigit():
        bot.reply_to(message, "Invalid input. Please enter a numeric value between 1 and 30.")
        bot.register_next_step_handler(message, get_count, phone)
        return
   
    count = int(message.text)
    if 1 <= count <= 30:
        bot.reply_to(message, f"Starting bombing for phone: {phone}, count: {count}")
        update_user_usage(message.from_user.id)
       
        bombing_events[message.chat.id] = Event()
       
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("Cancel Bombing", callback_data="cancel_bombing")
        markup.add(cancel_button)
        bot.send_message(message.chat.id, "Bombing started. You can cancel it using the button below:", reply_markup=markup)
       
        Thread(target=bombing, args=(message.chat.id, phone, count, bombing_events[message.chat.id])).start()
    else:
        bot.reply_to(message, "Invalid input. Please enter a number between 1 and 30.")
        bot.register_next_step_handler(message, get_count, phone)


def bombing(chat_id, phone, count, stop_event):
    x = 0
    phone = f"+98{phone[1:]}"
    for j in range(count):
        if stop_event.is_set():
            bot.send_message(chat_id, "Bombing cancelled.")
            return
        for k in range(len(SMS_SERVICES)):
            Thread(target=getattr(sms, SMS_SERVICES[k]), args=[phone]).start()
        if (j != 0) and (j % 5) == 0:
            Thread(target=getattr(call, CALL_SERVICES[x]), args=[phone]).start()
            x = (x + 1) % len(CALL_SERVICES)
        sleep(0.2)
    bot.send_message(chat_id, "Bombing finished")
    del bombing_events[chat_id]
@bot.callback_query_handler(func=lambda call: call.data == "cancel_bombing")
def cancel_bombing_callback(call):
    chat_id = call.message.chat.id
    if chat_id in bombing_events:
        bombing_events[chat_id].set()
        bot.answer_callback_query(call.id, "Bombing is being cancelled...")
        bot.edit_message_text("Bombing cancelled", chat_id=chat_id, message_id=call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "No active bombing to cancel.")

def process_new_admin(message):
    if message.text.isdigit():
        new_admin_id = int(message.text)
        if is_admin(new_admin_id):
            bot.reply_to(message, f"User with ID {new_admin_id} is already an admin.")
        else:
            add_admin(new_admin_id)
            bot.reply_to(message, f"Admin with ID {new_admin_id} has been added.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric ID.")

def process_broadcast(message):
    broadcast_message = message.text
    users = execute_db_query('SELECT user_id FROM users WHERE is_blocked = FALSE', fetch=True)
    success_count = 0
    fail_count = 0
    for user in users:
        try:
            bot.send_message(user[0], broadcast_message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send message to user {user[0]}: {e}")
            fail_count += 1
        sleep(0.1)  # Add a small delay to avoid hitting rate limits
    bot.reply_to(message, f"Broadcast message sent. Success: {success_count}, Failed: {fail_count}")

def process_set_user_limit_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        bot.reply_to(message, f"Enter the custom limit for user {user_id}:")
        bot.register_next_step_handler(message, process_set_user_limit, user_id)
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric user ID.")

def process_set_user_limit(message, user_id):
    if message.text.isdigit():
        limit = int(message.text)
        set_custom_limit(user_id, limit)
        bot.reply_to(message, f"Custom limit for user {user_id} has been set to {limit}.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric limit.")

def process_set_global_limit(message):
    if message.text.isdigit():
        limit = int(message.text)
        execute_db_query('UPDATE users SET custom_limit = %s', (limit,))
        bot.reply_to(message, f"Global limit has been set to {limit} for all users.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric limit.")

if __name__ == "__main__":
    setup_database()
    add_admin(6157703844)  # Add your admin ID here
    logger.info("Bot is starting...")
    run_bot()
