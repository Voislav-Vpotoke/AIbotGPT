import telebot
import os
import re
import requests
import openai
import sqlite3
import time
from dotenv import load_dotenv
from telebot import types
from loguru import logger

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger.add("bot.log", rotation="1 MB")  # Логирование в файл с ротацией

# Проверка загрузки переменных окружения
admin_usernames = os.getenv("ADMIN_USERNAMES", "")
logger.info(f"Loaded admin usernames: {admin_usernames}")


# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS allowed_users (username TEXT PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            direction TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


# Функции для работы с базой данных
def log_message(username, message, direction):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO messages (username, message, direction) VALUES (?, ?, ?)",
                  (username, message, direction))
        conn.commit()
        conn.close()
        logger.debug(f"Logged message from {username} (direction: {direction}): {message}")
    except Exception as e:
        logger.error(f"Error logging message: {e}")


def fetch_dialogue(username):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT message, direction, timestamp FROM messages WHERE username = ? ORDER BY timestamp",
                  (username,))
        messages = c.fetchall()
        conn.close()
        dialogue = []
        for message, direction, timestamp in messages:
            dialogue.append(f"{timestamp} {'Входящее' if direction == 'incoming' else 'Исходящее'}: {message}")
        logger.debug(f"Fetched dialogue for {username}: {dialogue}")
        return "\n".join(dialogue)
    except Exception as e:
        logger.error(f"Error fetching dialogue: {e}")
        return "Ошибка при загрузке диалога."


def add_user_to_db(username):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO allowed_users (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding user to database: {e}")


def remove_user_from_db(username):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("DELETE FROM allowed_users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error removing user from database: {e}")


def delete_messages_user(username):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        logger.info(f"Все сообщения пользователя {username} удалены.")
    except Exception as e:
        logger.error(f"Error deleting messages for user: {e}")


def is_user_allowed(username):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    logger.debug(f"Admin usernames: {admin_usernames}")
    if username in admin_usernames:
        return True
    else:
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT username FROM allowed_users WHERE username = ?", (username,))
            user = c.fetchone()
            conn.close()
            return user is not None
        except Exception as e:
            logger.error(f"Error checking if user is allowed: {e}")
            return False


def get_all_users():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT username FROM allowed_users")
        users = c.fetchall()
        conn.close()
        return [user[0] for user in users]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


# Инициализация базы данных
init_db()


def load_document_text(url: str) -> str:
    """Загружает текст документа по URL Google Docs."""
    match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
    if match_ is None:
        raise ValueError('Invalid Google Docs URL')
    doc_id = match_.group(1)
    response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
    response.raise_for_status()
    return response.text


# Проверка и загрузка API ключей
api_key = os.getenv("YOUR_API_KEY")
if api_key is None:
    raise Exception("API key for OpenAI is not set.")
openai.api_key = api_key

# Загрузка системного документа
try:
    system = load_document_text(
        'https://docs.google.com/document/')
except Exception as e:
    logger.error(f"Error loading documents: {e}")
    raise


class TelegramBot:
    def __init__(self, gpt_instance):
        self.gpt = gpt_instance
        token = os.getenv("YOUR_BOT_TOKEN")
        if token is None:
            raise Exception("Telegram Bot Token не определен в переменных окружения")
        self.bot = telebot.TeleBot(token)


bot = TelegramBot(gpt_instance=openai).bot
chat_histories = {}
chat_summaries = {}
dialog_states = {}


# Функция для создания инлайн клавиатуры
def create_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    add_button = types.InlineKeyboardButton("Добавить юзера", callback_data="add_user")
    remove_button = types.InlineKeyboardButton("Удалить юзера", callback_data="remove_user")
    view_button = types.InlineKeyboardButton("Посмотреть диалог", callback_data="view_dialogue")
    delete_messages_button = types.InlineKeyboardButton("Удалить сообщения", callback_data="delete_messages")
    list_users_button = types.InlineKeyboardButton("Список юзеров", callback_data="list_users")
    keyboard.add(add_button, remove_button)
    keyboard.add(view_button)
    keyboard.add(delete_messages_button)
    keyboard.add(list_users_button)
    return keyboard


# Обработчик команды /admin
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    username = message.from_user.username
    logger.debug(f"Username: {username}")
    if username in admin_usernames:
        keyboard = create_inline_keyboard()
        bot.send_message(message.chat.id, "Панель администратора:", reply_markup=keyboard)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


# Обработчик инлайн кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    username = call.from_user.username  # Добавляем правильное получение имени пользователя
    logger.debug(f"Callback from username: {username}")

    if call.data == "add_user":
        msg = bot.send_message(call.message.chat.id, "Введите имя пользователя для добавления:")
        bot.register_next_step_handler(msg, process_add_user)
    elif call.data == "remove_user":
        msg = bot.send_message(call.message.chat.id, "Введите имя пользователя для удаления:")
        bot.register_next_step_handler(msg, process_remove_user)
    elif call.data == "view_dialogue":
        msg = bot.send_message(call.message.chat.id, "Введите имя пользователя для просмотра диалога:")
        bot.register_next_step_handler(msg, process_view_dialogue)
    elif call.data == "delete_messages":
        msg = bot.send_message(call.message.chat.id, "Введите имя пользователя для удаления всех сообщений:")
        bot.register_next_step_handler(msg, process_delete_messages)
    elif call.data == "list_users":
        process_list_users(call.message, username)


def process_add_user(message):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    username = message.from_user.username
    logger.debug(f"process_add_user: {username}")
    if username in admin_usernames:
        new_user = message.text
        add_user_to_db(new_user)
        bot.reply_to(message, f"Пользователь {new_user} добавлен в список разрешенных.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_remove_user(message):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    username = message.from_user.username
    logger.debug(f"process_remove_user: {username}")
    if username in admin_usernames:
        remove_user = message.text
        remove_user_from_db(remove_user)
        bot.reply_to(message, f"Пользователь {remove_user} удален из списка разрешенных.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_view_dialogue(message):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    username = message.from_user.username
    logger.debug(f"process_view_dialogue: {username}")
    if username in admin_usernames:
        view_user = message.text
        dialogue = fetch_dialogue(view_user)
        logger.debug(f"Dialogue for user {view_user}: {dialogue}")

        # Отправка диалога частями, если он слишком длинный
        MAX_MESSAGE_LENGTH = 4096
        if dialogue:
            if len(dialogue) > MAX_MESSAGE_LENGTH:
                parts = [dialogue[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(dialogue), MAX_MESSAGE_LENGTH)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, dialogue)
        else:
            bot.send_message(message.chat.id, "Нет диалога")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_delete_messages(message):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    username = message.from_user.username
    logger.debug(f"process_delete_messages: {username}")
    if username in admin_usernames:
        delete_user = message.text
        delete_messages_user(delete_user)
        bot.reply_to(message, f"Все сообщения пользователя {delete_user} удалены.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_list_users(message, username):
    admin_usernames = os.getenv("ADMIN_USERNAMES", "").split(',')
    logger.debug(f"process_list_users: {username}")
    if username in admin_usernames:
        users = get_all_users()
        users_list = "\n".join(users)
        bot.send_message(message.chat.id, f"Список всех пользователей:\n{users_list}")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


# Функция для отправки длинных сообщений с проверкой ссылок
def send_long_text(chat_id: int, text: str, bot):
    MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram
    contains_link = bool(re.search(r'http[s]?://', text))

    # Отправка сообщения, деление на части если необходимо
    if len(text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(chat_id=chat_id, text=text)
    else:
        parts = [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for part in parts:
            bot.send_message(chat_id=chat_id, text=part)

    # Проверка наличия ссылки
    if contains_link:
        time.sleep(10)  # Задержка в 10 секунд

        # Отправляем стикер
        sticker_file_id = 'CAACAgIAAxkBAAIeeGZ6eXPrVYYAAWRJIHuhRDscfGvq9wACzDcAAkQsqUpvTd4i2f0HnTUE'  # Замените на ваш file_id стикера
        bot.send_sticker(chat_id, sticker_file_id)

        # Отправляем текстовое сообщение отдельно
        magic_message = "IT сфера - это современная магия! Поздравляю! Ты большой молодец! Теперь ты знаешь в каком направлении тебе обучаться!"
        bot.send_message(chat_id, magic_message)

        # Устанавливаем состояние завершения диалога
        dialog_states[chat_id] = "finished"

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id

    # Отправляем стикер
    welcome_sticker_file_id = 'CAACAgIAAxkBAAIedWZ6eTB3dgFVRP0ammpMpEqFR138AAKxOgACR_2hSkN5bfKbzeJFNQQ'  # Замените на ваш file_id стикера
    bot.send_sticker(chat_id, welcome_sticker_file_id)

    # Отправляем текстовое сообщение отдельно
    welcome_message = """
Привет, я — Сова! 
Я прилетела к тебе из онлайн школы Реботика, в которой ребята изучают цифровые технологии и навыки XXI века, чтобы помочь тебе выбрать направлении или профессию, которые тебе подойдут наилучшим образом. Для этого просто ответь на несколько моих вопросов. Договорились?"""
    bot.send_message(chat_id, welcome_message, reply_markup=create_start_keyboard())

    # Сбрасываем состояние диалога при старте
    dialog_states[chat_id] = "waiting_for_agreement"


def create_start_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Хорошо"))
    return keyboard


def create_continue_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Погнали"))
    return keyboard


@bot.message_handler(func=lambda message: message.text == "Хорошо" and dialog_states.get(message.chat.id) == "waiting_for_agreement")
def agree_to_proceed(message):
    chat_id = message.chat.id
    dialog_states[chat_id] = "active"

    # Отправляем стикер
    agreement_sticker_file_id = 'CAACAgIAAxkBAAIBAWZ7DJZaAAGI3RVo0Ii9bhBgqb51-QAC1gADVp29Coi51dxle64lLwQ'  # Замените на ваш file_id стикера
    bot.send_sticker(chat_id, agreement_sticker_file_id)

    # Отправляем текстовое сообщение отдельно
    bot.send_message(chat_id, "Отлично! И чтобы у нас всё получилось, пожалуйста, отвечай честно! Начнём?", reply_markup=create_continue_keyboard())


@bot.message_handler(func=lambda message: message.text == "Погнали" and dialog_states.get(message.chat.id) == "active")
def start_questions(message):
    # Начало общения с GPT
    chat_id = message.chat.id
    username = message.from_user.username

    logger.info(f"Starting questions for {username}")

    # Продолжение логики общения с GPT и отправки вопросов и ответов
    bot.send_message(chat_id, "Отлично, начнём!")
    # Здесь будет логика общения с GPT


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    user_question = message.text
    chat_id = message.chat.id
    username = message.from_user.username

    # Проверяем состояние диалога
    if dialog_states.get(chat_id) == "finished":
        bot.send_message(chat_id,
                         "👇Ты уже завершил тестирование. Пожалуйста! Если хочешь пройти ещё раз, то нажми кнопку Старт в меню.")
        return

    if dialog_states.get(chat_id) in ["waiting_for_agreement", "active"]:
        return

    logger.info(f"Received message from {username}: {user_question}")

    if not is_user_allowed(username):
        bot.reply_to(message, "Вы не имеете доступа к этому боту.")
        return

    logger.info(f"Received message from {chat_id} ({username}): {user_question}")

    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        chat_summaries[chat_id] = ""

    chat_histories[chat_id].append(("user", user_question))
    log_message(username, user_question, 'incoming')

    # Обновление суммаризированной истории
    current_summary = f"{chat_summaries[chat_id]} User: {user_question}"
    if len(current_summary) > 5000:  # Увеличиваем ограничение длины суммаризации до 5000 символов
        current_summary = current_summary[-5000:]
    chat_summaries[chat_id] = current_summary

    # Формирование запроса к OpenAI
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Вопрос клиента: {current_summary}"}
    ]
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-2024-05-13",
            messages=messages,
            temperature=0.6,
            frequency_penalty=2.0
        )
        answer = completion.choices[0].message.content
        logger.info(f"Sending answer to {chat_id} ({username}): {answer}")
        chat_histories[chat_id].append(("bot", answer))
        chat_summaries[chat_id] += f" Bot: {answer}"
        log_message(username, answer, 'outgoing')
        send_long_text(chat_id, answer, bot)  # Используем send_long_text для отправки сообщения
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке вашего запроса. Попробуйте позже.")


bot.polling(none_stop=True)
