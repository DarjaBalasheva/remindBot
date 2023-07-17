import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CallbackContext, CallbackQueryHandler, CommandHandler
import os
from dotenv import load_dotenv
load_dotenv()

# Путь к JSON-файлу учетных данных Google Sheets
JSON_FILE = 'data.json'

# ID таблицы Google Sheets
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# Токен бота
TOKEN = os.getenv('TOKEN')

# Устанавливаем область видимости для доступа к Google Sheets

scope_str = os.getenv('SCOPE')
SCOPE = scope_str.split(',')

# Создаем объекты для взаимодействия с Google Sheets
credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, SCOPE)
client = gspread.authorize(credentials)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    update.message.reply_text('Привет! Я бот напоминаний.')

def set_reminder(update: Update, context: CallbackContext):
    """Обработчик команды /setreminder"""
    chat_id = update.message.chat_id

    # Получаем данные от пользователя
    text = update.message.text.split(' ', 1)[1]
    date, time, answer_time = text.split(',')
    answer_time = int(answer_time.strip())

    # Записываем данные в Google Sheets
    row = [str(chat_id), text, date, time, answer_time]
    sheet.append_row(row)

    # Устанавливаем таймер для напоминания
    job_queue = context.job_queue
    job = job_queue.run_once(reminder_callback, answer_time, context=chat_id)
    context.chat_data['job'] = job

    # Отправляем сообщение с клавиатурой
    keyboard = [
        [InlineKeyboardButton("Выполнено", callback_data='done')],
        [InlineKeyboardButton("Не сделано", callback_data='not_done')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Напоминание установлено.', reply_markup=reply_markup)

def reminder_callback(context: CallbackContext):
    """Функция обратного вызова для напоминания"""
    chat_id = context.job.context
    message = 'Время ответить на напоминание прошло.'

    # Отправляем сообщение об игнорировании
    context.bot.send_message(chat_id=chat_id, text=message)

def button_callback(update: Update, context: CallbackContext):
    """Обработчик нажатия на кнопку"""
    query = update.callback_query
    answer = query.data

    # Отменяем таймер напоминания
    context.chat_data['job'].schedule_removal()

    if answer == 'done':
        message = 'Выполнено.'
    elif answer == 'not_done':
        message = 'Не сделанно'

    # Отправляем сообщение менеджеру
    manager_chat_id = os.getenv('MANAGER_CHAT_ID')
    context.bot.send_message(chat_id=manager_chat_id, text=message)

    # Отвечаем пользователю
    query.answer()

# Создаем экземпляр Updater и регистрируем обработчики
updater = Updater(TOKEN)
dispatcher = updater.dispatcher # Здесь у меня возникает конфликт из-за несовпадения библиотек
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('setreminder', set_reminder))
dispatcher.add_handler(CallbackQueryHandler(button_callback))


updater.start_polling()
