import telebot
from threading import Thread
from Api import sms, call
from time import sleep
from inspect import getmembers, isfunction
import mysql.connector
from datetime import datetime, timedelta

bot_token = '7330729864:AAE1QK7hCAEFmtrpaXd9ZjMObzO864uqSo4'
bot = telebot.TeleBot(bot_token)
SMS_SERVICES = [i[0] for i in getmembers(sms, isfunction)]
CALL_SERVICES = [i[0] for i in getmembers(call, isfunction)]
MAIN_CHANNEL_ID = '@ExoShopVpn'
ADMIN_IDS = set([6157703844])  

DB_NAME = 'Exosms'
DB_HOST = 'localhost'
DB_USER = 'z0roday'
DB_PASS = 'z0roday@@123%&&&'

def setup_database():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS
    )
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT UNIQUE,
        numeric_id BIGINT,
        phone_number VARCHAR(20),
        last_use DATETIME,
        use_count INT DEFAULT 0,
        is_blocked BOOLEAN DEFAULT FALSE,
        block_until DATETIME
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
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def save_user(user_id, numeric_id, phone_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO users (user_id, numeric_id, phone_number, last_use, use_count)
    VALUES (%s, %s, %s, NOW(), 0)
    ON DUPLICATE KEY UPDATE numeric_id = %s, phone_number = %s
    ''', (user_id, numeric_id, phone_number, numeric_id, phone_number))
    conn.commit()
    conn.close()

def update_user_usage(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET last_use = NOW(), use_count = use_count + 1
    WHERE user_id = %s
    ''', (user_id,))
    conn.commit()
    conn.close()

def check_user_limit(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT use_count, last_use, is_blocked, block_until
    FROM users
    WHERE user_id = %s
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        use_count, last_use, is_blocked, block_until = result
        if is_blocked:
            if block_until and datetime.now() > block_until:
                unblock_user(user_id)
                return True
            return False
        if use_count >= 2:
            if datetime.now() - last_use > timedelta(hours=24):
                reset_user_usage(user_id)
                return True
            return False
        return True
    return True

def reset_user_usage(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET use_count = 0, last_use = NOW()
    WHERE user_id = %s
    ''', (user_id,))
    conn.commit()
    conn.close()

def ban_user(user_id, duration_minutes):
    conn = get_db_connection()
    cursor = conn.cursor()
    block_until = datetime.now() + timedelta(minutes=duration_minutes)
    cursor.execute('''
    UPDATE users 
    SET is_blocked = TRUE, block_until = %s
    WHERE user_id = %s
    ''', (block_until, user_id))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET is_blocked = FALSE, block_until = NULL
    WHERE user_id = %s
    ''', (user_id,))
    conn.commit()
    conn.close()

def block_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    block_until = datetime.now() + timedelta(hours=24)
    cursor.execute('''
    UPDATE users 
    SET is_blocked = TRUE, block_until = %s
    WHERE user_id = %s
    ''', (block_until, user_id))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET is_blocked = FALSE, block_until = NULL, use_count = 0
    WHERE user_id = %s
    ''', (user_id,))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    if check_membership(message.from_user.id):
        if message.from_user.id in ADMIN_IDS:
            bot.reply_to(message, f"Welcome, Admin {message.from_user.first_name}! You have full access.")
            show_admin_panel(message.chat.id)
        elif check_user_limit(message.from_user.id):
            bot.reply_to(message, f"Welcome! {message.from_user.first_name}\nPlease enter your phone number (11 digits):")
            save_user(message.from_user.id, message.from_user.id, None)
        else:
            bot.reply_to(message, "You have reached your usage limit. Please try again later.")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        github_button = telebot.types.InlineKeyboardButton(text='GitHub', url='https://github.com/z0roday')
        join_button = telebot.types.InlineKeyboardButton(text='Join Channel', url=f'https://t.me/{MAIN_CHANNEL_ID[1:]}')
        check_button = telebot.types.InlineKeyboardButton(text='I have become a member', callback_data='check_membership')
        markup.add(join_button, github_button, check_button)
        bot.reply_to(message, "Please join our channel first:", reply_markup=markup)

def show_admin_panel(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Admin Info"))
    markup.add(telebot.types.KeyboardButton("Broadcast"))
    markup.add(telebot.types.KeyboardButton("Add Admin"))
    markup.add(telebot.types.KeyboardButton("Ban User"))
    markup.add(telebot.types.KeyboardButton("Unban User"))  
    bot.send_message(chat_id, "Admin panel:", reply_markup=markup)

def process_ban_user_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, numeric_id FROM users WHERE numeric_id = %s', (user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            bot.reply_to(message, f"User found. User ID: {user[0]}, Numeric ID: {user[1]}")
            bot.reply_to(message, "Please enter the ban duration in minutes:")
            bot.register_next_step_handler(message, process_ban_duration, user[0])
        else:
            bot.reply_to(message, "User not found. Please check the numeric ID and try again.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric ID.")

def process_unban_user_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, numeric_id, is_blocked FROM users WHERE numeric_id = %s', (user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            if user[2]:  
                unban_user(user[0])
                bot.reply_to(message, f"User with ID {user[1]} has been unbanned.")
            else:
                bot.reply_to(message, f"User with ID {user[1]} is not currently banned.")
        else:
            bot.reply_to(message, "User not found. Please check the numeric ID and try again.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric ID.")

def process_ban_duration(message, user_id):
    if message.text.isdigit():
        duration = int(message.text)
        ban_user(user_id, duration)
        bot.reply_to(message, f"User with ID {user_id} has been banned for {duration} minutes.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a number for the ban duration in minutes.")


@bot.message_handler(func=lambda message: message.text == "Admin Info")
def admin_info_button(message):
    if message.from_user.id in ADMIN_IDS:
        admin_info_command(message)
    else:
        bot.reply_to(message, "You don't have permission to use this feature.")

@bot.message_handler(func=lambda message: message.text == "Broadcast")
def broadcast_button(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Please enter the message you want to broadcast to all users:")
        bot.register_next_step_handler(message, process_broadcast)
    else:
        bot.reply_to(message, "You don't have permission to use this feature.")

@bot.message_handler(func=lambda message: message.text == "Add Admin")
def add_admin_button(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Please enter the numeric ID of the new admin:")
        bot.register_next_step_handler(message, process_new_admin)
    else:
        bot.reply_to(message, "You don't have permission to use this feature.")

def check_membership(user_id):
    try:
        member = bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiException:
        return False

@bot.callback_query_handler(func=lambda call: call.data == 'check_membership')
def callback_check_membership(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "Great! You've joined the channel.")
        bot.send_message(call.message.chat.id, "Please enter your phone number (11 digits):")
        save_user(call.from_user.id, call.from_user.id, None)
    else:
        bot.answer_callback_query(call.id, "You haven't joined the channel yet. Please join and try again.")

@bot.message_handler(func=lambda message: message.text and message.text.isdigit() and len(message.text) == 11)
def get_phone(message):
    if not check_membership(message.from_user.id):
        start(message)
        return
    if not check_user_limit(message.from_user.id):
        bot.reply_to(message, "You have reached your usage limit. Please try again later.")
        return
    phone = message.text
    if phone in ("09938282310", "09932539709"):
        bot.send_message(message.chat.id, "Number Not Found!\n /start")
    else:
        save_user(message.from_user.id, message.from_user.id, phone)
        bot.reply_to(message, "Please enter a number between 1 and 30:")
        bot.register_next_step_handler(message, get_count, phone)

def get_count(message, phone):
    if not check_membership(message.from_user.id):
        start(message)
        return
    if not check_user_limit(message.from_user.id):
        bot.reply_to(message, "You have reached your usage limit. Please try again later.")
        return
    if message.text and message.text.isdigit() and 1 <= int(message.text) <= 30:
        count = int(message.text)
        bot.reply_to(message, f"Starting bombing for phone: {phone}, count: {count}")
        update_user_usage(message.from_user.id)
        Thread(target=bombing, args=(message.chat.id, phone, count)).start()
    else:
        bot.reply_to(message, "Invalid input. Please enter a number between 1 and 30.")
        bot.register_next_step_handler(message, get_count, phone)

def bombing(chat_id, phone, count):
    x = 0
    phone = f"+98{phone[1:]}"
    for j in range(count):
        for k in range(len(SMS_SERVICES)):
            Thread(target=getattr(sms, SMS_SERVICES[k]), args=[phone]).start()
        if (j != 0) and (j % 5) == 0:
            Thread(target=getattr(call, CALL_SERVICES[x]), args=[phone]).start()
            x += 1
            if x > len(CALL_SERVICES) - 1:
                x = 0
        sleep(0.2)
    bot.send_message(chat_id, "Bombing finished")

def process_new_admin(message):
    if message.text.isdigit():
        new_admin_id = int(message.text)
        add_admin(new_admin_id)
        bot.reply_to(message, f"Admin with ID {new_admin_id} has been added.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric ID.")

def process_broadcast(message):
    broadcast_message = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    for user in users:
        try:
            bot.send_message(user[0], broadcast_message)
        except Exception as e:
            print(f"Failed to send message to user {user[0]}: {e}")

    bot.reply_to(message, "Broadcast message sent to all users.")

if __name__ == "__main__":
    setup_database()
    ADMIN_IDS = load_admins()
    bot.polling()
