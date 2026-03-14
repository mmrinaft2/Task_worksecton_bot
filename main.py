#!/usr/bin/env python3
"""
Odoo Task Management Bot for Telegram
Converts user descriptions into well-structured technical specifications
"""

import os
import re
import json
import logging
import tempfile
import calendar
from datetime import datetime, date
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import langdetect
from langdetect import detect

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Worksection project ID
WS_PROJECT_ID = 222684
WS_PROJECT_NAME = 'Odoo'

from worksection_api import WorksectionAPI
from ai_agent import analyze_and_get_questions, generate_spec

ws_api = WorksectionAPI()

# Language-specific strings
TRANSLATIONS = {
    'uk': {
        'start': 'Привіт! 👋\n\nЯ допоможу тобі створити детальне технічне завдання для Odoo.\n\nОпиши проблему або ідею, яку ти хочеш реалізувати.',
        'select_category': '🎯 Вибери категорію:',
        'bug': '🐛 Bug (помилка)',
        'feature': '✨ Feature (нова функція)',
        'improvement': '⚡ Improvement (покращення)',
        'support': '🆘 Support (технічна підтримка)',
        'wait_description': 'Чекаю твого опису...',
        'questions_for_category': 'Щоб зробити ТЗ детальнішим, відповідь на кілька питань:',
        'provide_answer': 'Твоя відповідь (або напиши "пропустити" для переходу до наступного):',
        'file_uploaded': '✅ Файл завантажено: {filename}',
        'generating_ts': '⏳ Генерую технічне завдання...',
        'ts_generated': '📋 Ось готове ТЗ:\n\n',
        'confirm_ts': 'Все добре? Натисни кнопку:',
        'confirm': '✅ Так, все правильно',
        'edit': '✏️ Редагувати',
        'cancel': '❌ Скасувати',
        'ts_confirmed': '✅ ТЗ прийнято! \n\nНаступний крок: інтеграція з WorkSection/Odoo',
        'ts_cancelled': '❌ ТЗ скасовано.',
    },
    'en': {
        'start': 'Hello! 👋\n\nI will help you create a detailed technical specification for Odoo.\n\nDescribe the problem or idea you want to implement.',
        'select_category': '🎯 Select a category:',
        'bug': '🐛 Bug',
        'feature': '✨ Feature (new function)',
        'improvement': '⚡ Improvement',
        'support': '🆘 Support (technical support)',
        'wait_description': 'Waiting for your description...',
        'questions_for_category': 'To make the specification more detailed, please answer a few questions:',
        'provide_answer': 'Your answer (or type "skip" to move to the next):',
        'file_uploaded': '✅ File uploaded: {filename}',
        'generating_ts': '⏳ Generating technical specification...',
        'ts_generated': '📋 Here is the complete specification:\n\n',
        'confirm_ts': 'Everything correct? Click the button:',
        'confirm': '✅ Yes, all correct',
        'edit': '✏️ Edit',
        'cancel': '❌ Cancel',
        'ts_confirmed': '✅ Specification accepted! \n\nNext step: integration with WorkSection/Odoo',
        'ts_cancelled': '❌ Specification cancelled.',
    },
    'ru': {
        'start': 'Привет! 👋\n\nЯ помогу тебе создать детальное техническое задание для Odoo.\n\nОпиши проблему или идею, которую ты хочешь реализовать.',
        'select_category': '🎯 Выбери категорию:',
        'bug': '🐛 Bug (ошибка)',
        'feature': '✨ Feature (новая функция)',
        'improvement': '⚡ Improvement (улучшение)',
        'support': '🆘 Support (техническая поддержка)',
        'wait_description': 'Жду твоего описания...',
        'questions_for_category': 'Чтобы сделать ТЗ подробнее, ответь на несколько вопросов:',
        'provide_answer': 'Твой ответ (или напиши "пропустить" для перехода к следующему):',
        'file_uploaded': '✅ Файл загружен: {filename}',
        'generating_ts': '⏳ Генерирую техническое задание...',
        'ts_generated': '📋 Вот готовое ТЗ:\n\n',
        'confirm_ts': 'Все правильно? Нажми кнопку:',
        'confirm': '✅ Да, все правильно',
        'edit': '✏️ Редактировать',
        'cancel': '❌ Отменить',
        'ts_confirmed': '✅ ТЗ принято! \n\nСледующий шаг: интеграция с WorkSection/Odoo',
        'ts_cancelled': '❌ ТЗ отменено.',
    },
    'pl': {
        'start': 'Cześć! 👋\n\nPomogę Ci stworzyć szczegółową specyfikację techniczną dla Odoo.\n\nOpisz problem lub pomysł, który chcesz zrealizować.',
        'select_category': '🎯 Wybierz kategorię:',
        'bug': '🐛 Bug (błąd)',
        'feature': '✨ Feature (nowa funkcja)',
        'improvement': '⚡ Improvement (ulepszenie)',
        'support': '🆘 Support (pomoc techniczna)',
        'wait_description': 'Czekam na Twój opis...',
        'questions_for_category': 'Aby specyfikacja była bardziej szczegółowa, odpowiedz na kilka pytań:',
        'provide_answer': 'Twoja odpowiedź (lub napisz "pomiń" aby przejść do następnego):',
        'file_uploaded': '✅ Plik przesłany: {filename}',
        'generating_ts': '⏳ Generuję specyfikację techniczną...',
        'ts_generated': '📋 Oto gotowa specyfikacja:\n\n',
        'confirm_ts': 'Wszystko w porządku? Kliknij przycisk:',
        'confirm': '✅ Tak, wszystko poprawnie',
        'edit': '✏️ Edytuj',
        'cancel': '❌ Anuluj',
        'ts_confirmed': '✅ Specyfikacja przyjęta!\n\nNastępny krok: integracja z WorkSection/Odoo',
        'ts_cancelled': '❌ Specyfikacja anulowana.',
    }
}

# Category-specific questions
CATEGORY_QUESTIONS = {
    'bug': {
        'uk': [
            '🐛 В якому модулі Odoo знаходиться помилка?',
            '📍 Як відтворити проблему? (Крок за кроком)',
            '🎯 Який очікуваний результат?',
            '⚠️ Яких дані/налаштування використовуються?',
        ],
        'en': [
            '🐛 In which Odoo module is the bug located?',
            '📍 How to reproduce the issue? (Step by step)',
            '🎯 What is the expected result?',
            '⚠️ What data/settings are used?',
        ],
        'ru': [
            '🐛 В каком модуле Odoo находится ошибка?',
            '📍 Как воспроизвести проблему? (Пошагово)',
            '🎯 Какой ожидаемый результат?',
            '⚠️ Какие данные/настройки используются?',
        ]
    },
    'feature': {
        'uk': [
            '✨ Яка мета цієї функції?',
            '👥 Хто буде це використовувати?',
            '🔧 Як це має інтегруватися з Odoo?',
            '📊 Які дані потрібні для цього?',
        ],
        'en': [
            '✨ What is the goal of this feature?',
            '👥 Who will use this?',
            '🔧 How should this integrate with Odoo?',
            '📊 What data is needed for this?',
        ],
        'ru': [
            '✨ Какова цель этой функции?',
            '👥 Кто будет это использовать?',
            '🔧 Как это должно интегрироваться с Odoo?',
            '📊 Какие данные нужны для этого?',
        ]
    },
    'improvement': {
        'uk': [
            '⚡ Що потрібно покращити?',
            '🎯 Чому це важливо?',
            '📈 Як це буде вимірюватися (швидкість, зручність...)?',
            '🔄 Як це впливає на поточний workflow?',
        ],
        'en': [
            '⚡ What needs to be improved?',
            '🎯 Why is this important?',
            '📈 How will this be measured (speed, convenience...)?',
            '🔄 How does this affect the current workflow?',
        ],
        'ru': [
            '⚡ Что нужно улучшить?',
            '🎯 Почему это важно?',
            '📈 Как это будет измеряться (скорость, удобство...)?',
            '🔄 Как это влияет на текущий workflow?',
        ]
    },
    'support': {
        'uk': [
            '🆘 Яке питання у тебе?',
            '🔍 Що ти вже спробував(а)?',
            '⚙️ Які налаштування Odoo у тебе?',
            '📝 Який очікуваний результат?',
        ],
        'en': [
            '🆘 What is your question?',
            '🔍 What have you already tried?',
            '⚙️ What are your Odoo settings?',
            '📝 What is the expected result?',
        ],
        'ru': [
            '🆘 Какой у тебя вопрос?',
            '🔍 Что ты уже попробовал(а)?',
            '⚙️ Какие настройки Odoo у тебя?',
            '📝 Какой ожидаемый результат?',
        ]
    }
}


def _reset_task_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset all task-related data for next task"""
    context.user_data['description'] = None
    context.user_data['category'] = None
    context.user_data['answers'] = {}
    context.user_data['files'] = []
    context.user_data['file_ids'] = []
    context.user_data['links'] = []
    context.user_data['priority'] = 5
    context.user_data['deadline'] = ''
    context.user_data['current_question_index'] = 0


MONTH_NAMES = {
    'uk': ['Січень','Лютий','Березень','Квітень','Травень','Червень',
           'Липень','Серпень','Вересень','Жовтень','Листопад','Грудень'],
    'en': ['January','February','March','April','May','June',
           'July','August','September','October','November','December'],
    'ru': ['Январь','Февраль','Март','Апрель','Май','Июнь',
           'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],
    'pl': ['Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec',
           'Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'],
}

DAY_NAMES = {
    'uk': ['Пн','Вт','Ср','Чт','Пт','Сб','Нд'],
    'en': ['Mo','Tu','We','Th','Fr','Sa','Su'],
    'ru': ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'],
    'pl': ['Pn','Wt','Śr','Cz','Pt','So','Nd'],
}


def build_calendar(year: int, month: int, lang: str) -> InlineKeyboardMarkup:
    """Build an inline calendar keyboard for given month"""
    keyboard = []

    # Header: prev < Month Year > next
    month_name = MONTH_NAMES.get(lang, MONTH_NAMES['uk'])[month - 1]
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    keyboard.append([
        InlineKeyboardButton('◀', callback_data=f'cal_nav_{prev_year}_{prev_month:02d}'),
        InlineKeyboardButton(f'{month_name} {year}', callback_data='cal_ignore'),
        InlineKeyboardButton('▶', callback_data=f'cal_nav_{next_year}_{next_month:02d}'),
    ])

    # Day names row
    day_names = DAY_NAMES.get(lang, DAY_NAMES['uk'])
    keyboard.append([InlineKeyboardButton(d, callback_data='cal_ignore') for d in day_names])

    # Days grid
    today = date.today()
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(' ', callback_data='cal_ignore'))
            else:
                d = date(year, month, day)
                label = f'*{day}*' if d == today else str(day)
                # Block past dates
                if d < today:
                    row.append(InlineKeyboardButton('·', callback_data='cal_ignore'))
                else:
                    row.append(InlineKeyboardButton(
                        str(day),
                        callback_data=f'cal_day_{year}_{month:02d}_{day:02d}'
                    ))
        keyboard.append(row)

    # Skip button
    skip_text = {'uk': '⏭ Пропустити', 'en': '⏭ Skip', 'ru': '⏭ Пропустить', 'pl': '⏭ Pomiń'}.get(lang, '⏭ Пропустити')
    keyboard.append([InlineKeyboardButton(skip_text, callback_data='cal_skip')])

    return InlineKeyboardMarkup(keyboard)


async def ask_deadline_calendar(message, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Show calendar for deadline selection"""
    today = date.today()
    markup = build_calendar(today.year, today.month, lang)
    ask_text = {
        'uk': '📅 Оберіть термін виконання:',
        'en': '📅 Select deadline:',
        'ru': '📅 Выберите срок выполнения:',
        'pl': '📅 Wybierz termin realizacji:',
    }.get(lang, '📅 Оберіть термін виконання:')
    context.user_data['status'] = 'selecting_deadline'
    await message.reply_text(ask_text, reply_markup=markup)


async def handle_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle calendar button clicks"""
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get('lang', 'uk')

    if data == 'cal_ignore':
        return

    elif data.startswith('cal_nav_'):
        # Navigate to different month
        _, _, year, month = data.split('_')
        markup = build_calendar(int(year), int(month), lang)
        await query.edit_message_reply_markup(reply_markup=markup)

    elif data.startswith('cal_day_'):
        # Day selected
        _, _, year, month, day = data.split('_')
        selected = date(int(year), int(month), int(day))
        deadline_str = selected.strftime('%d.%m.%Y')
        context.user_data['deadline'] = deadline_str

        deadline_label = {'uk': f'📅 Термін: {deadline_str}',
                          'en': f'📅 Deadline: {deadline_str}',
                          'ru': f'📅 Срок: {deadline_str}',
                          'pl': f'📅 Termin: {deadline_str}'}.get(lang, f'📅 {deadline_str}')
        await query.edit_message_text(text=deadline_label)

        # Proceed to generate TS
        await generate_ts_after_deadline(query.message, context, lang)

    elif data == 'cal_skip':
        context.user_data['deadline'] = ''
        skip_label = {'uk': '📅 Без терміну', 'en': '📅 No deadline', 'ru': '📅 Без срока', 'pl': '📅 Bez terminu'}.get(lang, '📅 Без терміну')
        await query.edit_message_text(text=skip_label)
        await generate_ts_after_deadline(query.message, context, lang)


async def generate_ts_after_deadline(message, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Generate AI-powered TS after deadline is set"""
    description = context.user_data.get('description', '')
    category = context.user_data.get('category', 'feature')
    answers = context.user_data.get('answers', {})
    files = context.user_data.get('files', [])
    deadline = context.user_data.get('deadline', '')
    questions = context.user_data.get('ai_questions') or \
                CATEGORY_QUESTIONS.get(category, {}).get(lang, [])

    # Show generating message
    generating_text = {
        'uk': '⏳ Генерую технічне завдання як Odoo-архітектор...',
        'en': '⏳ Generating technical specification as Odoo architect...',
        'ru': '⏳ Генерирую техническое задание как Odoo-архитектор...',
        'pl': '⏳ Generuję specyfikację techniczną jako architekt Odoo...',
    }.get(lang, '⏳ Генерую ТЗ...')
    thinking_msg = await message.reply_text(generating_text)

    # Generate spec via AI
    title, spec_text = await generate_spec(
        description=description,
        category=category,
        questions=questions,
        answers=answers,
        deadline=deadline,
        lang=lang,
    )

    # Append files info if any
    if files:
        files_block = f"\n\n📎 **ВКЛАДЕННЯ:** {len(files)} файл(и)\n"
        files_block += '\n'.join(f"   • {f}" for f in files)
        spec_text += files_block

    context.user_data['ts_text'] = spec_text
    context.user_data['task_title'] = title
    context.user_data['status'] = 'confirming_ts'

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    await message.reply_text(t('ts_generated', lang) + spec_text, parse_mode='Markdown')

    keyboard = [
        [InlineKeyboardButton(t('confirm', lang), callback_data='confirm_ts')],
        [InlineKeyboardButton(t('edit', lang), callback_data='edit_ts')],
        [InlineKeyboardButton(t('cancel', lang), callback_data='cancel_ts')],
    ]
    await message.reply_text(t('confirm_ts', lang), reply_markup=InlineKeyboardMarkup(keyboard))


def get_language(user_text: str) -> str:
    """Detect user's language"""
    try:
        lang = detect(user_text)
        lang_map = {'uk': 'uk', 'en': 'en', 'ru': 'ru', 'pl': 'pl'}
        return lang_map.get(lang, 'en')
    except:
        return 'en'


def t(key: str, lang: str, **kwargs) -> str:
    """Get translated string"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text


MAIN_MENU_TEXT = {
    'uk': '📋 Головне меню\n\nОбери дію:',
    'en': '📋 Main menu\n\nChoose an action:',
    'ru': '📋 Главное меню\n\nВыбери действие:',
    'pl': '📋 Menu główne\n\nWybierz akcję:',
}

MAIN_MENU_BUTTONS = {
    'uk': ['📝 Створити задачу', '📂 Мої задачі'],
    'en': ['📝 Create task', '📂 My tasks'],
    'ru': ['📝 Создать задачу', '📂 Мои задачи'],
    'pl': ['📝 Utwórz zadanie', '📂 Moje zadania'],
}


MENU_DELAY_SECONDS = 600  # 10 minutes


def _schedule_main_menu(context: ContextTypes.DEFAULT_TYPE, chat_id: int, lang: str) -> None:
    """Schedule main menu to appear after delay"""
    # Remove any existing scheduled menu for this chat
    jobs = context.job_queue.get_jobs_by_name(f'menu_{chat_id}')
    for job in jobs:
        job.schedule_removal()

    context.job_queue.run_once(
        _delayed_main_menu_callback,
        when=MENU_DELAY_SECONDS,
        chat_id=chat_id,
        name=f'menu_{chat_id}',
        data={'lang': lang},
    )


async def _delayed_main_menu_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback for delayed main menu"""
    job = context.job
    chat_id = job.chat_id
    lang = job.data.get('lang', 'uk')

    buttons = MAIN_MENU_BUTTONS.get(lang, MAIN_MENU_BUTTONS['uk'])
    keyboard = [
        [InlineKeyboardButton(buttons[0], callback_data='menu_new_task')],
        [InlineKeyboardButton(buttons[1], callback_data='menu_my_tasks')],
    ]
    text = MAIN_MENU_TEXT.get(lang, MAIN_MENU_TEXT['uk'])
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_main_menu(message, context: ContextTypes.DEFAULT_TYPE, lang: str, welcome: str = None) -> None:
    """Show main menu with buttons"""
    _reset_task_data(context)
    context.user_data['status'] = 'main_menu'

    buttons = MAIN_MENU_BUTTONS.get(lang, MAIN_MENU_BUTTONS['uk'])
    keyboard = [
        [InlineKeyboardButton(buttons[0], callback_data='menu_new_task')],
        [InlineKeyboardButton(buttons[1], callback_data='menu_my_tasks')],
    ]
    text = welcome or MAIN_MENU_TEXT.get(lang, MAIN_MENU_TEXT['uk'])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu button clicks"""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'uk')

    if query.data == 'menu_new_task':
        _reset_task_data(context)
        context.user_data['status'] = 'waiting_description'
        await query.edit_message_text(text=t('start', lang))

    elif query.data == 'menu_my_tasks':
        await query.edit_message_text(text={
            'uk': '⏳ Завантажую список задач...',
            'en': '⏳ Loading task list...',
            'ru': '⏳ Загружаю список задач...',
            'pl': '⏳ Ładuję listę zadań...',
        }.get(lang, '⏳ Loading...'))
        await show_tasks_list(query.message, context, lang)


TASK_STATUS_LABELS = {
    'uk': {'active': '🟢 Активна', 'done': '✅ Виконана', 'closed': '🔒 Закрита'},
    'en': {'active': '🟢 Active', 'done': '✅ Done', 'closed': '🔒 Closed'},
    'ru': {'active': '🟢 Активная', 'done': '✅ Выполнена', 'closed': '🔒 Закрыта'},
    'pl': {'active': '🟢 Aktywne', 'done': '✅ Wykonane', 'closed': '🔒 Zamknięte'},
}

PRIORITY_ICONS = {
    '0': '⬜', '1': '🟦', '2': '🟦', '3': '🟩',
    '4': '🟩', '5': '🟨', '6': '🟨', '7': '🟧', '8': '🟧', '9': '🟥', '10': '🔴',
}

PRIORITY_LABELS = {
    'uk': {
        '0': '⬜ Без пріоритету', '1': '🟦 Мінімальний', '2': '🟦 Низький',
        '3': '🟩 Нижче середнього', '4': '🟩 Середній', '5': '🟨 Нормальний',
        '6': '🟨 Вище середнього', '7': '🟧 Високий', '8': '🟧 Терміново',
        '9': '🟥 Критичний', '10': '🔴 Блокер',
    },
    'en': {
        '0': '⬜ No priority', '1': '🟦 Minimal', '2': '🟦 Low',
        '3': '🟩 Below average', '4': '🟩 Medium', '5': '🟨 Normal',
        '6': '🟨 Above average', '7': '🟧 High', '8': '🟧 Urgent',
        '9': '🟥 Critical', '10': '🔴 Blocker',
    },
    'ru': {
        '0': '⬜ Без приоритета', '1': '🟦 Минимальный', '2': '🟦 Низкий',
        '3': '🟩 Ниже среднего', '4': '🟩 Средний', '5': '🟨 Нормальный',
        '6': '🟨 Выше среднего', '7': '🟧 Высокий', '8': '🟧 Срочно',
        '9': '🟥 Критический', '10': '🔴 Блокер',
    },
    'pl': {
        '0': '⬜ Brak priorytetu', '1': '🟦 Minimalny', '2': '🟦 Niski',
        '3': '🟩 Poniżej średniego', '4': '🟩 Średni', '5': '🟨 Normalny',
        '6': '🟨 Powyżej średniego', '7': '🟧 Wysoki', '8': '🟧 Pilne',
        '9': '🟥 Krytyczny', '10': '🔴 Bloker',
    },
}

TASKS_PAGE_SIZE = 8


async def show_tasks_list(message, context: ContextTypes.DEFAULT_TYPE, lang: str, page: int = 0) -> None:
    """Fetch tasks from Worksection and show paginated list"""
    result = ws_api.get_tasks(WS_PROJECT_ID)

    if result.get('status') != 'ok':
        error_msg = result.get('message', 'Unknown error')
        error_text = {
            'uk': f'❌ Помилка завантаження задач: {error_msg}',
            'en': f'❌ Error loading tasks: {error_msg}',
            'ru': f'❌ Ошибка загрузки задач: {error_msg}',
            'pl': f'❌ Błąd ładowania zadań: {error_msg}',
        }.get(lang, f'❌ Error: {error_msg}')
        await message.reply_text(error_text)
        return

    tasks = result.get('data', [])
    if not tasks:
        empty_text = {
            'uk': '📭 Задач у проєкті поки немає.',
            'en': '📭 No tasks in the project yet.',
            'ru': '📭 Задач в проекте пока нет.',
            'pl': '📭 Brak zadań w projekcie.',
        }.get(lang, '📭 No tasks.')
        await message.reply_text(empty_text)
        return

    # Sort: active first, then by priority descending (critical on top)
    active_tasks = [t for t in tasks if t.get('status') == 'active']
    done_tasks = [t for t in tasks if t.get('status') != 'active']
    active_tasks.sort(key=lambda t: int(t.get('priority', '5')), reverse=True)
    done_tasks.sort(key=lambda t: t.get('date_added', ''), reverse=True)
    tasks_sorted = active_tasks + done_tasks

    # Store tasks for later reference
    context.user_data['task_list'] = tasks_sorted
    context.user_data['tasks_page'] = page

    # Paginate
    total = len(tasks_sorted)
    start_idx = page * TASKS_PAGE_SIZE
    end_idx = min(start_idx + TASKS_PAGE_SIZE, total)
    page_tasks = tasks_sorted[start_idx:end_idx]

    # Build task buttons with priority number (like in Worksection)
    keyboard = []
    for task in page_tasks:
        task_id = task.get('id', '')
        task_name = task.get('name', 'Без назви')[:42]
        priority = str(task.get('priority', '5'))
        if task.get('status') == 'done':
            label = f"✅ {task_name}"
        else:
            label = f"[{priority}] {task_name}"
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f'task_view_{task_id}')
        ])

    # Pagination buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton('◀ ', callback_data=f'tasks_page_{page - 1}'))
    if end_idx < total:
        nav_row.append(InlineKeyboardButton(' ▶', callback_data=f'tasks_page_{page + 1}'))
    if nav_row:
        keyboard.append(nav_row)

    # Back to menu button
    back_text = {'uk': '↩️ Назад', 'en': '↩️ Back', 'ru': '↩️ Назад', 'pl': '↩️ Wstecz'}.get(lang, '↩️ Back')
    keyboard.append([InlineKeyboardButton(back_text, callback_data='menu_back')])

    legend_map = {
        'uk': '[число] — пріоритет (10 = блокер, 1 = мінімальний)  ✅ = виконана',
        'en': '[number] — priority (10 = blocker, 1 = minimal)  ✅ = done',
        'ru': '[число] — приоритет (10 = блокер, 1 = минимальный)  ✅ = выполнена',
        'pl': '[liczba] — priorytet (10 = bloker, 1 = minimalny)  ✅ = wykonane',
    }
    legend = legend_map.get(lang, legend_map['uk'])

    header_text = {
        'uk': f'📂 Задачі проєкту ({start_idx + 1}–{end_idx} з {total}):\n\n{legend}',
        'en': f'📂 Project tasks ({start_idx + 1}–{end_idx} of {total}):\n\n{legend}',
        'ru': f'📂 Задачи проекта ({start_idx + 1}–{end_idx} из {total}):\n\n{legend}',
        'pl': f'📂 Zadania projektu ({start_idx + 1}–{end_idx} z {total}):\n\n{legend}',
    }.get(lang, f'📂 Tasks ({start_idx + 1}–{end_idx} of {total}):\n\n{legend}')

    context.user_data['status'] = 'viewing_tasks'
    await message.reply_text(header_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_tasks_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task list pagination and task detail viewing"""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'uk')

    if query.data.startswith('tasks_page_'):
        page = int(query.data.split('_')[2])
        try:
            await query.message.delete()
        except Exception:
            pass
        await show_tasks_list(query.message, context, lang, page)

    elif query.data.startswith('task_view_'):
        task_id = query.data.split('_')[2]
        await query.edit_message_text(text={
            'uk': '⏳ Завантажую деталі задачі...',
            'en': '⏳ Loading task details...',
            'ru': '⏳ Загружаю детали задачи...',
            'pl': '⏳ Ładuję szczegóły zadania...',
        }.get(lang, '⏳ Loading...'))
        await show_task_details(query.message, context, lang, task_id)

    elif query.data == 'tasks_back_list':
        page = context.user_data.get('tasks_page', 0)
        try:
            await query.message.delete()
        except Exception:
            pass
        await show_tasks_list(query.message, context, lang, page)

    elif query.data == 'menu_back':
        try:
            await query.message.delete()
        except Exception:
            pass
        await show_main_menu(query.message, context, lang)


async def show_task_details(message, context: ContextTypes.DEFAULT_TYPE, lang: str, task_id: str) -> None:
    """Fetch and display task details from Worksection"""
    result = ws_api.get_task(int(task_id))

    if result.get('status') != 'ok':
        error_msg = result.get('message', 'Unknown error')
        await message.reply_text(f'❌ {error_msg}')
        return

    task = result.get('data', {})
    task_name = task.get('name', '—')
    task_status_raw = task.get('status', 'active')
    status_labels = TASK_STATUS_LABELS.get(lang, TASK_STATUS_LABELS['uk'])
    task_status = status_labels.get(task_status_raw, task_status_raw)
    priority_labels = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['uk'])
    task_priority = priority_labels.get(str(task.get('priority', '5')), '🟨 Нормальний')
    date_added = task.get('date_added', '—')
    date_end = task.get('date_end', '')
    user_from = task.get('user_from', {}).get('name', '—')
    user_to = task.get('user_to', {}).get('name', '—')
    task_page = task.get('page', '')

    # Build detail text
    detail_labels = {
        'uk': {
            'status': 'Статус', 'priority': 'Пріоритет', 'created': 'Створена',
            'deadline': 'Дедлайн', 'author': 'Автор', 'assigned': 'Виконавець',
            'no_deadline': 'Не встановлено',
        },
        'en': {
            'status': 'Status', 'priority': 'Priority', 'created': 'Created',
            'deadline': 'Deadline', 'author': 'Author', 'assigned': 'Assigned to',
            'no_deadline': 'Not set',
        },
        'ru': {
            'status': 'Статус', 'priority': 'Приоритет', 'created': 'Создана',
            'deadline': 'Дедлайн', 'author': 'Автор', 'assigned': 'Исполнитель',
            'no_deadline': 'Не установлен',
        },
        'pl': {
            'status': 'Status', 'priority': 'Priorytet', 'created': 'Utworzono',
            'deadline': 'Termin', 'author': 'Autor', 'assigned': 'Wykonawca',
            'no_deadline': 'Nie ustawiono',
        },
    }
    lbl = detail_labels.get(lang, detail_labels['uk'])
    deadline_text = date_end if date_end else lbl['no_deadline']

    ws_link = f"https://{(os.getenv('WS_ACCOUNT_DOMAIN') or '').strip('/')}{task_page}" if task_page else ''

    text = (
        f"📋 *{task_name}*\n\n"
        f"*{lbl['status']}:* {task_status}\n"
        f"*{lbl['priority']}:* {task_priority}\n"
        f"*{lbl['created']}:* {date_added}\n"
        f"*{lbl['deadline']}:* {deadline_text}\n"
        f"*{lbl['author']}:* {user_from}\n"
        f"*{lbl['assigned']}:* {user_to}\n"
    )
    if ws_link:
        link_label = {'uk': 'Відкрити у Worksection', 'en': 'Open in Worksection',
                      'ru': 'Открыть в Worksection', 'pl': 'Otwórz w Worksection'}.get(lang, 'Open')
        text += f"\n🔗 [{link_label}]({ws_link})"

    # Buttons
    back_text = {'uk': '↩️ До списку задач', 'en': '↩️ Back to task list',
                 'ru': '↩️ К списку задач', 'pl': '↩️ Do listy zadań'}.get(lang, '↩️ Back')
    keyboard = [[InlineKeyboardButton(back_text, callback_data='tasks_back_list')]]

    await message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    user_id = update.effective_user.id
    lang = 'uk'  # Default to Ukrainian

    context.user_data['user_id'] = user_id
    context.user_data['lang'] = lang
    context.user_data['status'] = 'main_menu'
    context.user_data['category'] = None
    context.user_data['description'] = None
    context.user_data['answers'] = {}
    context.user_data['files'] = []
    context.user_data['file_ids'] = []
    context.user_data['links'] = []
    context.user_data['priority'] = 5
    context.user_data['deadline'] = ''

    welcome = t('start', lang)
    await show_main_menu(update.message, context, lang, welcome)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages"""
    message_text = update.message.text
    await _process_text_message(update, context, message_text)


async def _process_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Process text (from text message or voice transcription)"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Cancel any scheduled main menu — user is active
    jobs = context.job_queue.get_jobs_by_name(f'menu_{chat_id}')
    for job in jobs:
        job.schedule_removal()

    # Initialize user context if not exists
    if 'lang' not in context.user_data:
        context.user_data['lang'] = get_language(message_text)
        context.user_data['status'] = 'waiting_description'
        context.user_data['user_id'] = user_id
        context.user_data['description'] = None
        context.user_data['answers'] = {}
        context.user_data['category'] = None
        context.user_data['files'] = []

    lang = context.user_data.get('lang', 'uk')
    status = context.user_data.get('status', 'waiting_description')

    if status == 'main_menu':
        # User typed text instead of pressing button — treat as new task description
        _reset_task_data(context)
        context.user_data['status'] = 'waiting_description'
        status = 'waiting_description'

    if status == 'waiting_description':
        # Keep existing files if editing
        saved_files = context.user_data.get('files', [])
        saved_file_ids = context.user_data.get('file_ids', [])
        saved_links = context.user_data.get('links', [])
        _reset_task_data(context)
        if saved_files:
            context.user_data['files'] = saved_files
            context.user_data['file_ids'] = saved_file_ids
            context.user_data['links'] = saved_links
        context.user_data['description'] = message_text
        await analyze_task(update, context, lang)

    elif status == 'waiting_link':
        # User sends a link for large file
        if 'links' not in context.user_data:
            context.user_data['links'] = []
        # Extract URLs from message
        urls = re.findall(r'https?://\S+', message_text)
        if urls:
            context.user_data['links'].extend(urls)
            added_text = {
                'uk': f'🔗 Посилання додано ({len(urls)}). Можеш надіслати ще або продовжити.',
                'en': f'🔗 Link added ({len(urls)}). You can send more or continue.',
                'ru': f'🔗 Ссылка добавлена ({len(urls)}). Можешь отправить ещё или продолжить.',
                'pl': f'🔗 Link dodany ({len(urls)}). Możesz wysłać więcej lub kontynuować.',
            }.get(lang, '🔗 Link added.')
            # Restore previous status
            prev_status = context.user_data.get('prev_status', 'waiting_description')
            context.user_data['status'] = prev_status
            await update.message.reply_text(added_text)
        else:
            hint_text = {
                'uk': '⚠️ Не бачу посилання. Надішли URL (починається з https://)',
                'en': '⚠️ No link found. Send a URL (starting with https://)',
                'ru': '⚠️ Не вижу ссылки. Отправь URL (начинается с https://)',
                'pl': '⚠️ Nie widzę linku. Wyślij URL (zaczynający się od https://)',
            }.get(lang, '⚠️ No link found.')
            await update.message.reply_text(hint_text)
        return

    elif status == 'answering_questions':
        question_index = context.user_data.get('current_question_index', 0)
        if message_text.lower() in ['пропустити', 'skip', 'пропустить', 'pomiń']:
            context.user_data['answers'][question_index] = None
        else:
            context.user_data['answers'][question_index] = message_text

        question_index += 1
        # Use AI-generated questions if available
        questions = context.user_data.get('ai_questions') or \
                    CATEGORY_QUESTIONS.get(context.user_data.get('category'), {}).get(lang, [])

        if question_index < len(questions):
            context.user_data['current_question_index'] = question_index
            await update.message.reply_text(
                f"{questions[question_index]}\n\n{t('provide_answer', lang)}"
            )
        else:
            await generate_ts(update, context, lang)


async def analyze_task(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """AI analyzes the task: auto-detect category and generate questions"""
    description = context.user_data.get('description', '')

    thinking_text = {
        'uk': '🤔 Аналізую задачу як Odoo-архітектор...',
        'en': '🤔 Analyzing task as Odoo architect...',
        'ru': '🤔 Анализирую задачу как Odoo-архитектор...',
        'pl': '🤔 Analizuję zadanie jako architekt Odoo...',
    }.get(lang, '🤔 Аналізую...')

    thinking_msg = await update.message.reply_text(thinking_text)

    # AI determines category and generates questions
    category, ai_questions = await analyze_and_get_questions(description, lang)

    context.user_data['category'] = category
    context.user_data['current_question_index'] = 0
    context.user_data['status'] = 'answering_questions'

    # Fallback to static questions if AI fails
    if not ai_questions:
        ai_questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])

    context.user_data['ai_questions'] = ai_questions

    category_emoji = {'bug': '🐛', 'feature': '✨', 'improvement': '⚡', 'support': '🆘'}.get(category, '📌')

    if ai_questions:
        provide_answer = t('provide_answer', lang)
        await thinking_msg.edit_text(
            f"{category_emoji} Категорія: {category.upper()}\n\n"
            f"{t('questions_for_category', lang)}\n\n"
            f"{ai_questions[0]}\n\n"
            f"{provide_answer}"
        )
    else:
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await generate_ts(update, context, lang)


async def generate_ts(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Ask for deadline via calendar, then generate TS"""
    await ask_deadline_calendar(update.message, context, lang)


async def _generate_ts_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Legacy TS generator (kept for reference)"""
    await update.message.reply_text(t('generating_ts', lang))

    description = context.user_data.get('description', '')
    category = context.user_data.get('category', 'feature')
    answers = context.user_data.get('answers', {})
    files = context.user_data.get('files', [])

    ts_text = f"""═══════════════════════════════════════
          ТЕХНІЧНЕ ЗАВДАННЯ
═══════════════════════════════════════

📌 КАТЕГОРІЯ: {category.upper()}
📝 ОПИС: {description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 ДОДАТКОВІ ДЕТАЛІ:
"""

    questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])
    for idx, question in enumerate(questions):
        answer = answers.get(idx)
        if answer:
            ts_text += f"\n{question}\n➜ {answer}\n"


    if files:
        ts_text += f"\n📎 ФАЙЛИ: {len(files)} файл(и)\n"
        for file_name in files:
            ts_text += f"   • {file_name}\n"
    
    ts_text += "═══════════════════════════════════════"
    
    context.user_data['ts_text'] = ts_text
    context.user_data['status'] = 'confirming_ts'
    
    # Send TS and ask for confirmation
    await update.message.reply_text(t('ts_generated', lang) + ts_text)
    
    keyboard = [
        [InlineKeyboardButton(t('confirm', lang), callback_data='confirm_ts')],
        [InlineKeyboardButton(t('edit', lang), callback_data='edit_ts')],
        [InlineKeyboardButton(t('cancel', lang), callback_data='cancel_ts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(t('confirm_ts', lang), reply_markup=reply_markup)


async def handle_ts_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TS confirmation"""
    query = update.callback_query
    action = query.data.split('_')[0] + '_' + query.data.split('_')[1]
    
    lang = context.user_data.get('lang', 'uk')
    
    if action == 'confirm_ts':
        await query.answer()
        context.user_data['status'] = 'creating_task'
        await query.edit_message_text(text='⏳ Створюю задачу у Worksection...')

        description = context.user_data.get('description', '')
        category = context.user_data.get('category', 'feature')
        answers = context.user_data.get('answers', {})
        priority = context.user_data.get('priority', 5)
        deadline = context.user_data.get('deadline', '')
        links = context.user_data.get('links', [])
        file_ids = context.user_data.get('file_ids', [])

        # Use AI-generated title or fallback
        title = context.user_data.get('task_title') or \
                description[:100].split('.')[0].split('\n')[0].strip()

        # Build task body
        questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])
        body = f"Категорія: {category.upper()}\n\n{description}"
        for idx, q in enumerate(questions):
            ans = answers.get(idx)
            if ans:
                body += f"\n\n{q}\n➜ {ans}"
        if links:
            body += "\n\nПосилання:\n" + "\n".join(f"- {l}" for l in links)

        # Download files from Telegram
        attach_files = {}
        temp_paths = []
        skipped_files = []
        if file_ids:
            for idx, (file_id, filename) in enumerate(file_ids):
                try:
                    tg_file = await context.bot.get_file(file_id)
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    await tg_file.download_to_drive(temp_path)
                    attach_files[f'attach[{idx}]'] = (filename, open(temp_path, 'rb'))
                    temp_paths.append(temp_path)
                except Exception as e:
                    logger.error(f"Failed to download file {filename}: {e}")
                    skipped_files.append(filename)

        if skipped_files:
            body += "\n\nФайли не прикріплені (завеликі для Telegram API):\n"
            body += "\n".join(f"- {f}" for f in skipped_files)

        # Send to Worksection
        result = ws_api.post_task(
            id_project=WS_PROJECT_ID,
            title=title,
            text=body,
            priority=priority,
            dateend=deadline,
            files=attach_files if attach_files else None,
        )

        # Cleanup temp files
        for val in attach_files.values():
            val[1].close()
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass

        # Reset task data for next task
        _reset_task_data(context)
        context.user_data['status'] = 'waiting_description'

        if result.get('status') == 'ok':
            task_data = result.get('data', {})
            task_link = task_data.get('page', '')
            ws_url = f"https://aclima.worksection.com{task_link}" if task_link else ""
            link_text = f"\n🔗 {ws_url}" if ws_url else ""
            success_text = {
                'uk': f'✅ Задачу створено у Worksection!\n📂 Проект: {WS_PROJECT_NAME}{link_text}',
                'en': f'✅ Task created in Worksection!\n📂 Project: {WS_PROJECT_NAME}{link_text}',
                'ru': f'✅ Задача создана в Worksection!\n📂 Проект: {WS_PROJECT_NAME}{link_text}',
                'pl': f'✅ Zadanie utworzone w Worksection!\n📂 Projekt: {WS_PROJECT_NAME}{link_text}',
            }.get(lang, f'✅ Task created!{link_text}')
            await query.message.reply_text(success_text)
        else:
            error_msg = result.get('message', 'Unknown error')
            error_text = {
                'uk': f'❌ Помилка при створенні задачі: {error_msg}',
                'en': f'❌ Error creating task: {error_msg}',
                'ru': f'❌ Ошибка при создании задачи: {error_msg}',
                'pl': f'❌ Błąd tworzenia zadania: {error_msg}',
            }.get(lang, f'❌ Error: {error_msg}')
            await query.message.reply_text(error_text)

        # Schedule main menu to appear after 10 minutes
        _schedule_main_menu(context, query.message.chat_id, lang)
        
    elif action == 'edit_ts':
        await query.answer()
        # Keep files, description and links — only reset answers
        context.user_data['answers'] = {}
        context.user_data['current_question_index'] = 0
        context.user_data['status'] = 'waiting_description'
        edit_text = {
            'uk': '✏️ Опиши задачу заново або надішли уточнення.\nФайли збережено.',
            'en': '✏️ Describe the task again or send clarifications.\nFiles are kept.',
            'ru': '✏️ Опиши задачу заново или отправь уточнения.\nФайлы сохранены.',
            'pl': '✏️ Opisz zadanie ponownie lub wyślij uściślenia.\nPliki zachowane.',
        }.get(lang, '✏️ Опиши задачу заново.')
        await query.edit_message_text(text=edit_text)

    elif action == 'cancel_ts':
        await query.answer()
        await query.edit_message_text(text=t('ts_cancelled', lang))
        _schedule_main_menu(context, query.message.chat_id, lang)


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file, photo and video uploads"""
    lang = context.user_data.get('lang', 'uk')

    if 'files' not in context.user_data:
        context.user_data['files'] = []
    if 'file_ids' not in context.user_data:
        context.user_data['file_ids'] = []

    filename = None
    file_id = None

    if update.message.document:
        filename = update.message.document.file_name
        file_id = update.message.document.file_id
    elif update.message.photo:
        photo = update.message.photo[-1]
        filename = f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
        file_id = photo.file_id
    elif update.message.video:
        video = update.message.video
        filename = video.file_name or f"video_{datetime.now().strftime('%H%M%S')}.mp4"
        file_id = video.file_id

    if filename:
        # Check file size — Telegram Bot API limit is 20 MB
        file_size = None
        if update.message.document:
            file_size = update.message.document.file_size
        elif update.message.video:
            file_size = update.message.video.file_size
        elif update.message.photo:
            file_size = update.message.photo[-1].file_size

        context.user_data['files'].append(filename)
        if file_id:
            context.user_data['file_ids'].append((file_id, filename))

        if file_size and file_size > 20 * 1024 * 1024:
            # Remove from file_ids — can't download it
            context.user_data['file_ids'] = [
                (fid, fn) for fid, fn in context.user_data['file_ids'] if fid != file_id
            ]
            warn_text = {
                'uk': (f'⚠️ Файл "{filename}" завеликий ({file_size // (1024*1024)} МБ).\n\n'
                       f'Завантаж його на Google Drive та надішли мені посилання — я додам його до задачі.'),
                'en': (f'⚠️ File "{filename}" is too large ({file_size // (1024*1024)} MB).\n\n'
                       f'Upload it to Google Drive and send me the link — I will add it to the task.'),
                'ru': (f'⚠️ Файл "{filename}" слишком большой ({file_size // (1024*1024)} МБ).\n\n'
                       f'Загрузи его на Google Drive и отправь мне ссылку — я добавлю её в задачу.'),
                'pl': (f'⚠️ Plik "{filename}" jest za duży ({file_size // (1024*1024)} MB).\n\n'
                       f'Prześlij go na Google Drive i wyślij mi link — dodam go do zadania.'),
            }.get(lang, f'⚠️ File too large: {filename}')
            context.user_data['prev_status'] = context.user_data.get('status', 'waiting_description')
            context.user_data['status'] = 'waiting_link'
            await update.message.reply_text(warn_text)
        else:
            await update.message.reply_text(
                t('file_uploaded', lang, filename=filename)
            )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages — transcribe with Whisper and process as text"""
    lang = context.user_data.get('lang', 'uk')

    transcribing_text = {
        'uk': '🎤 Розпізнаю голосове повідомлення...',
        'en': '🎤 Transcribing voice message...',
        'ru': '🎤 Распознаю голосовое сообщение...',
        'pl': '🎤 Rozpoznaję wiadomość głosową...',
    }.get(lang, '🎤 Розпізнаю...')

    thinking_msg = await update.message.reply_text(transcribing_text)

    try:
        from openai import AsyncOpenAI
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        temp_path = os.path.join(tempfile.gettempdir(), f"voice_{update.message.voice.file_id}.ogg")
        await voice_file.download_to_drive(temp_path)

        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        with open(temp_path, 'rb') as audio:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
            )
        text = transcript.text.strip()

        try:
            os.remove(temp_path)
        except Exception:
            pass

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        if not text:
            error_text = {
                'uk': '⚠️ Не вдалося розпізнати голосове повідомлення. Спробуй ще раз або напиши текстом.',
                'en': '⚠️ Could not transcribe voice message. Try again or type text.',
                'ru': '⚠️ Не удалось распознать голосовое сообщение. Попробуй ещё раз или напиши текстом.',
                'pl': '⚠️ Nie udało się rozpoznać wiadomości głosowej. Spróbuj ponownie lub napisz tekstem.',
            }.get(lang, '⚠️ Не вдалося розпізнати.')
            await update.message.reply_text(error_text)
            return

        # Show transcribed text and process it
        recognized_label = {
            'uk': '🎤 Розпізнано',
            'en': '🎤 Recognized',
            'ru': '🎤 Распознано',
            'pl': '🎤 Rozpoznano',
        }.get(lang, '🎤')
        await update.message.reply_text(f"{recognized_label}: {text}")

        # Process as text message
        await _process_text_message(update, context, text)

    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        error_text = {
            'uk': f'⚠️ Помилка розпізнавання: {e}',
            'en': f'⚠️ Transcription error: {e}',
            'ru': f'⚠️ Ошибка распознавания: {e}',
            'pl': f'⚠️ Błąd rozpoznawania: {e}',
        }.get(lang, f'⚠️ Error: {e}')
        await update.message.reply_text(error_text)


def main() -> None:
    """Start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_tasks_navigation, pattern='^(tasks_page_|task_view_|tasks_back_list|menu_back)'))
    application.add_handler(CallbackQueryHandler(handle_main_menu, pattern='^menu_'))
    application.add_handler(CallbackQueryHandler(handle_calendar, pattern='^cal_'))
    application.add_handler(CallbackQueryHandler(handle_ts_confirmation, pattern='^(confirm|edit|cancel)_'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(MessageHandler(filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.VIDEO, handle_file))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
