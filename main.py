#!/usr/bin/env python3
"""
Odoo Task Management Bot for Telegram
Converts user descriptions into well-structured technical specifications
and creates tasks in Worksection
"""

import os
import re
import json
import logging
import tempfile
from datetime import datetime
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

from worksection_api import WorksectionAPI

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

# Worksection API client
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
        'ts_confirmed': '✅ ТЗ прийнято!',
        'ts_cancelled': '❌ ТЗ скасовано.',
        'select_priority': '🔥 Наскільки це терміново?',
        'priority_low': '🟢 Низький (1-2)',
        'priority_normal': '🔵 Нормальний (3-4)',
        'priority_medium': '🟡 Середній (5-6)',
        'priority_high': '🟠 Високий (7-8)',
        'priority_critical': '🔴 Критичний (9-10)',
        'select_project': '📂 Вибери проект у Worksection:',
        'no_projects': '⚠️ Не вдалося отримати список проектів. Перевір налаштування API.',
        'creating_task': '⏳ Створюю задачу у Worksection...',
        'task_created': '✅ Задачу створено у Worksection!\n\n📂 Проект: {project}\n📌 Пріоритет: {priority}\n🔗 Посилання: {link}',
        'task_error': '❌ Помилка при створенні задачі: {error}',
        'ask_deadline': '📅 Який термін виконання? (формат: ДД.ММ.РРРР)\n\nНаприклад: 25.03.2026\n\nАбо напиши "пропустити" щоб не вказувати.',
        'deadline_set': '📅 Термін: {deadline}',
        'deadline_skipped': '📅 Без терміну',
        'deadline_invalid': '⚠️ Невірний формат дати. Спробуй ще раз (ДД.ММ.РРРР):',
        'ask_links': '🔗 Є посилання для перегляду? (URL сторінок, скрінів тощо)\n\nНадішли посилання або напиши "пропустити".',
        'links_added': '🔗 Посилання додано: {count}',
        'links_skipped': '🔗 Без посилань',
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
        'ts_confirmed': '✅ Specification accepted!',
        'ts_cancelled': '❌ Specification cancelled.',
        'select_priority': '🔥 How urgent is this?',
        'priority_low': '🟢 Low (1-2)',
        'priority_normal': '🔵 Normal (3-4)',
        'priority_medium': '🟡 Medium (5-6)',
        'priority_high': '🟠 High (7-8)',
        'priority_critical': '🔴 Critical (9-10)',
        'select_project': '📂 Select a Worksection project:',
        'no_projects': '⚠️ Could not fetch project list. Check API settings.',
        'creating_task': '⏳ Creating task in Worksection...',
        'task_created': '✅ Task created in Worksection!\n\n📂 Project: {project}\n📌 Priority: {priority}\n🔗 Link: {link}',
        'task_error': '❌ Error creating task: {error}',
        'ask_deadline': '📅 What is the deadline? (format: DD.MM.YYYY)\n\nExample: 25.03.2026\n\nOr type "skip" to skip.',
        'deadline_set': '📅 Deadline: {deadline}',
        'deadline_skipped': '📅 No deadline',
        'deadline_invalid': '⚠️ Invalid date format. Try again (DD.MM.YYYY):',
        'ask_links': '🔗 Any links to review? (page URLs, screenshots, etc.)\n\nSend links or type "skip".',
        'links_added': '🔗 Links added: {count}',
        'links_skipped': '🔗 No links',
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
        'ts_confirmed': '✅ ТЗ принято!',
        'ts_cancelled': '❌ ТЗ отменено.',
        'select_priority': '🔥 Насколько это срочно?',
        'priority_low': '🟢 Низкий (1-2)',
        'priority_normal': '🔵 Нормальный (3-4)',
        'priority_medium': '🟡 Средний (5-6)',
        'priority_high': '🟠 Высокий (7-8)',
        'priority_critical': '🔴 Критический (9-10)',
        'select_project': '📂 Выбери проект в Worksection:',
        'no_projects': '⚠️ Не удалось получить список проектов. Проверь настройки API.',
        'creating_task': '⏳ Создаю задачу в Worksection...',
        'task_created': '✅ Задача создана в Worksection!\n\n📂 Проект: {project}\n📌 Приоритет: {priority}\n🔗 Ссылка: {link}',
        'task_error': '❌ Ошибка при создании задачи: {error}',
        'ask_deadline': '📅 Какой срок выполнения? (формат: ДД.ММ.ГГГГ)\n\nНапример: 25.03.2026\n\nИли напиши "пропустить" чтобы не указывать.',
        'deadline_set': '📅 Срок: {deadline}',
        'deadline_skipped': '📅 Без срока',
        'deadline_invalid': '⚠️ Неверный формат даты. Попробуй ещё раз (ДД.ММ.ГГГГ):',
        'ask_links': '🔗 Есть ссылки для просмотра? (URL страниц, скринов и т.д.)\n\nОтправь ссылки или напиши "пропустить".',
        'links_added': '🔗 Ссылки добавлены: {count}',
        'links_skipped': '🔗 Без ссылок',
    },
    'pl': {
        'start': 'Cześć! 👋\n\nPomogę Ci stworzyć szczegółową specyfikację techniczną dla Odoo.\n\nOpisz problem lub pomysł, który chcesz zrealizować.',
        'select_category': '🎯 Wybierz kategorię:',
        'bug': '🐛 Bug (błąd)',
        'feature': '✨ Feature (nowa funkcja)',
        'improvement': '⚡ Improvement (ulepszenie)',
        'support': '🆘 Support (wsparcie techniczne)',
        'wait_description': 'Czekam na Twój opis...',
        'questions_for_category': 'Aby specyfikacja była bardziej szczegółowa, odpowiedz na kilka pytań:',
        'provide_answer': 'Twoja odpowiedź (lub napisz "pomiń" aby przejść dalej):',
        'file_uploaded': '✅ Plik przesłany: {filename}',
        'generating_ts': '⏳ Generuję specyfikację techniczną...',
        'ts_generated': '📋 Oto gotowa specyfikacja:\n\n',
        'confirm_ts': 'Wszystko w porządku? Kliknij przycisk:',
        'confirm': '✅ Tak, wszystko poprawnie',
        'edit': '✏️ Edytuj',
        'cancel': '❌ Anuluj',
        'ts_confirmed': '✅ Specyfikacja zatwierdzona!',
        'ts_cancelled': '❌ Specyfikacja anulowana.',
        'select_priority': '🔥 Jak pilne jest to zadanie?',
        'priority_low': '🟢 Niski (1-2)',
        'priority_normal': '🔵 Normalny (3-4)',
        'priority_medium': '🟡 Średni (5-6)',
        'priority_high': '🟠 Wysoki (7-8)',
        'priority_critical': '🔴 Krytyczny (9-10)',
        'select_project': '📂 Wybierz projekt w Worksection:',
        'no_projects': '⚠️ Nie udało się pobrać listy projektów. Sprawdź ustawienia API.',
        'creating_task': '⏳ Tworzę zadanie w Worksection...',
        'task_created': '✅ Zadanie utworzone w Worksection!\n\n📂 Projekt: {project}\n📌 Priorytet: {priority}\n🔗 Link: {link}',
        'task_error': '❌ Błąd przy tworzeniu zadania: {error}',
        'ask_deadline': '📅 Jaki jest termin realizacji? (format: DD.MM.RRRR)\n\nNa przykład: 25.03.2026\n\nLub napisz "pomiń" aby pominąć.',
        'deadline_set': '📅 Termin: {deadline}',
        'deadline_skipped': '📅 Bez terminu',
        'deadline_invalid': '⚠️ Nieprawidłowy format daty. Spróbuj ponownie (DD.MM.RRRR):',
        'ask_links': '🔗 Czy są linki do przejrzenia? (URL stron, zrzuty ekranu itp.)\n\nWyślij linki lub napisz "pomiń".',
        'links_added': '🔗 Linki dodane: {count}',
        'links_skipped': '🔗 Bez linków',
    }
}

# Priority mapping: callback_data -> (value, label)
PRIORITY_MAP = {
    'priority_low': 2,
    'priority_normal': 4,
    'priority_medium': 6,
    'priority_high': 8,
    'priority_critical': 10,
}

PRIORITY_LABELS = {
    'uk': {2: 'Низький', 4: 'Нормальний', 6: 'Середній', 8: 'Високий', 10: 'Критичний'},
    'en': {2: 'Low', 4: 'Normal', 6: 'Medium', 8: 'High', 10: 'Critical'},
    'ru': {2: 'Низкий', 4: 'Нормальный', 6: 'Средний', 8: 'Высокий', 10: 'Критический'},
    'pl': {2: 'Niski', 4: 'Normalny', 6: 'Średni', 8: 'Wysoki', 10: 'Krytyczny'},
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
        ],
        'pl': [
            '🐛 W którym module Odoo występuje błąd?',
            '📍 Jak odtworzyć problem? (Krok po kroku)',
            '🎯 Jaki jest oczekiwany rezultat?',
            '⚠️ Jakie dane/ustawienia są używane?',
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
        ],
        'pl': [
            '✨ Jaki jest cel tej funkcji?',
            '👥 Kto będzie z tego korzystać?',
            '🔧 Jak ma się to integrować z Odoo?',
            '📊 Jakie dane są potrzebne?',
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
        ],
        'pl': [
            '⚡ Co trzeba ulepszyć?',
            '🎯 Dlaczego to jest ważne?',
            '📈 Jak to będzie mierzone (szybkość, wygoda...)?',
            '🔄 Jak to wpływa na obecny workflow?',
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
        ],
        'pl': [
            '🆘 Jakie masz pytanie?',
            '🔍 Co już próbowałeś/aś?',
            '⚙️ Jakie masz ustawienia Odoo?',
            '📝 Jaki jest oczekiwany rezultat?',
        ]
    }
}


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command — ask user to select language"""
    user_id = update.effective_user.id

    context.user_data['user_id'] = user_id
    context.user_data['lang'] = None
    context.user_data['status'] = 'selecting_language'
    context.user_data['category'] = None
    context.user_data['description'] = None
    context.user_data['answers'] = {}
    context.user_data['files'] = []
    context.user_data['priority'] = None
    context.user_data['project_id'] = None

    keyboard = [
        [InlineKeyboardButton('🇺🇦 Українська', callback_data='lang_uk')],
        [InlineKeyboardButton('🇬🇧 English', callback_data='lang_en')],
        [InlineKeyboardButton('🇺🇦 Русский', callback_data='lang_ru')],
        [InlineKeyboardButton('🇵🇱 Polski', callback_data='lang_pl')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🌐 Виберіть мову / Select language / Wybierz język:', reply_markup=reply_markup)


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()

    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    context.user_data['status'] = 'waiting_description'

    await query.edit_message_text(text=t('start', lang))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages"""
    user_id = update.effective_user.id
    message_text = update.message.text

    # If language not selected yet, prompt to use /start
    if not context.user_data.get('lang'):
        await update.message.reply_text('Please use /start to begin / Натисни /start щоб почати')
        return

    lang = context.user_data.get('lang', 'uk')
    status = context.user_data.get('status', 'waiting_description')

    if status == 'waiting_description':
        context.user_data['description'] = message_text
        await ask_priority(update, context, lang)

    elif status == 'waiting_deadline':
        if message_text.lower() in ['пропустити', 'skip', 'пропустить', 'pomiń']:
            context.user_data['deadline'] = ''
            await update.message.reply_text(t('deadline_skipped', lang))
            # Ask for links
            context.user_data['status'] = 'waiting_links'
            await update.message.reply_text(t('ask_links', lang))
        else:
            try:
                parsed = datetime.strptime(message_text.strip(), '%d.%m.%Y')
                context.user_data['deadline'] = message_text.strip()
                await update.message.reply_text(t('deadline_set', lang, deadline=message_text.strip()))
                # Ask for links
                context.user_data['status'] = 'waiting_links'
                await update.message.reply_text(t('ask_links', lang))
            except ValueError:
                await update.message.reply_text(t('deadline_invalid', lang))

    elif status == 'waiting_links':
        if message_text.lower() in ['пропустити', 'skip', 'пропустить', 'pomiń']:
            context.user_data['links'] = []
            await update.message.reply_text(t('links_skipped', lang))
            await _generate_and_confirm(update.message, context, lang)
        else:
            # Extract URLs from message
            urls = re.findall(r'https?://[^\s]+', message_text)
            if not urls:
                # Treat the whole message as a link if it looks like one
                urls = [message_text.strip()]
            if 'links' not in context.user_data:
                context.user_data['links'] = []
            context.user_data['links'].extend(urls)
            await update.message.reply_text(t('links_added', lang, count=len(urls)))
            await _generate_and_confirm(update.message, context, lang)


async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Ask user to select category"""
    keyboard = [
        [InlineKeyboardButton(t('bug', lang), callback_data='category_bug')],
        [InlineKeyboardButton(t('feature', lang), callback_data='category_feature')],
        [InlineKeyboardButton(t('improvement', lang), callback_data='category_improvement')],
        [InlineKeyboardButton(t('support', lang), callback_data='category_support')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['status'] = 'category_selected'
    await update.message.reply_text(t('select_category', lang), reply_markup=reply_markup)


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category selection"""
    query = update.callback_query
    await query.answer()

    category = query.data.split('_')[1]
    context.user_data['category'] = category
    context.user_data['current_question_index'] = 0
    context.user_data['status'] = 'answering_questions'

    lang = context.user_data.get('lang', 'uk')
    questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])

    if questions:
        await query.edit_message_text(
            text=t('questions_for_category', lang) + '\n\n' +
                 questions[0] + '\n\n' +
                 t('provide_answer', lang)
        )
    else:
        await ask_priority(update, context, lang)


async def ask_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask category-specific questions"""
    lang = context.user_data.get('lang', 'uk')
    await ask_category(update, context, lang)


async def ask_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Ask user to select priority (urgency)"""
    keyboard = [
        [InlineKeyboardButton(t('priority_low', lang), callback_data='priority_low')],
        [InlineKeyboardButton(t('priority_normal', lang), callback_data='priority_normal')],
        [InlineKeyboardButton(t('priority_medium', lang), callback_data='priority_medium')],
        [InlineKeyboardButton(t('priority_high', lang), callback_data='priority_high')],
        [InlineKeyboardButton(t('priority_critical', lang), callback_data='priority_critical')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['status'] = 'selecting_priority'
    await update.message.reply_text(t('select_priority', lang), reply_markup=reply_markup)


async def handle_priority_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle priority selection"""
    query = update.callback_query
    await query.answer()

    priority_key = query.data
    priority_value = PRIORITY_MAP.get(priority_key, 5)
    context.user_data['priority'] = priority_value

    lang = context.user_data.get('lang', 'uk')
    priority_label = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['en']).get(priority_value, '')

    await query.edit_message_text(text=f"🔥 {priority_label}")

    # Auto-select Odoo project
    ODOO_PROJECT_ID = 222684
    ODOO_PROJECT_NAME = 'Odoo'
    context.user_data['project_id'] = ODOO_PROJECT_ID
    context.user_data['projects_map'] = {str(ODOO_PROJECT_ID): ODOO_PROJECT_NAME}

    # Ask for deadline
    context.user_data['status'] = 'waiting_deadline'
    await query.message.reply_text(t('ask_deadline', lang))


async def handle_project_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle project selection"""
    query = update.callback_query
    await query.answer()

    project_id = int(query.data.split('_')[1])
    context.user_data['project_id'] = project_id

    lang = context.user_data.get('lang', 'uk')
    project_name = context.user_data.get('projects_map', {}).get(str(project_id), '')

    await query.edit_message_text(text=f"📂 {project_name}")

    # Generate TS and show for confirmation
    await generate_ts_from_query(query, context, lang)


async def _generate_and_confirm(message, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Generate TS and show confirmation buttons"""
    await message.reply_text(t('generating_ts', lang))
    ts_text = _build_ts_text(context, lang)
    context.user_data['ts_text'] = ts_text
    context.user_data['status'] = 'confirming_ts'

    await message.reply_text(t('ts_generated', lang) + ts_text)
    await _send_confirmation_buttons(message, context, lang)


async def generate_ts_from_query(query, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Generate technical specification (called from callback query)"""
    await _generate_and_confirm(query.message, context, lang)


def _extract_title(description: str) -> str:
    """Extract short title from description (first sentence, max 100 chars)"""
    # Split by sentence endings
    for sep in ['. ', '.\n', '! ', '!\n', '? ', '?\n', '\n']:
        if sep in description:
            title = description[:description.index(sep)].strip()
            if len(title) > 10:
                return title[:100]
    # If no sentence break, take first 100 chars
    return description[:100].strip()


def _build_ts_text(context: ContextTypes.DEFAULT_TYPE, lang: str) -> str:
    """Build the TS text for preview in Telegram"""
    description = context.user_data.get('description', '')
    files = context.user_data.get('files', [])
    priority = context.user_data.get('priority', 5)
    priority_label = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['en']).get(priority, '')
    title = _extract_title(description)
    deadline = context.user_data.get('deadline', '')

    # Preview for Telegram
    ts_text = f"📌 Тема: {title}\n"
    ts_text += f"🔥 Пріоритет: {priority_label} ({priority}/10)\n"
    if deadline:
        ts_text += f"📅 Термін: {deadline}\n"
    ts_text += f"\n📝 Опис:\n{description}\n"

    links = context.user_data.get('links', [])
    if links:
        ts_text += f"\n🔗 Посилання:\n"
        for link in links:
            ts_text += f"   • {link}\n"

    if files:
        ts_text += f"\n📎 Файли: {len(files)}\n"
        for file_name in files:
            ts_text += f"   • {file_name}\n"

    # Save title separately for Worksection
    context.user_data['task_title'] = title

    return ts_text


def _build_ws_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Build task body for Worksection (description + links + file names)"""
    description = context.user_data.get('description', '')
    links = context.user_data.get('links', [])
    files = context.user_data.get('files', [])

    text = description

    if links:
        text += "\n\nПосилання:\n"
        for link in links:
            text += f"- {link}\n"

    if files:
        text += "\n\nФайли:\n"
        for file_name in files:
            text += f"- {file_name}\n"

    return text


async def _send_confirmation_buttons(message, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Send confirmation buttons"""
    keyboard = [
        [InlineKeyboardButton(t('confirm', lang), callback_data='confirm_ts')],
        [InlineKeyboardButton(t('edit', lang), callback_data='edit_ts')],
        [InlineKeyboardButton(t('cancel', lang), callback_data='cancel_ts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(t('confirm_ts', lang), reply_markup=reply_markup)


async def handle_ts_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TS confirmation — create task in Worksection"""
    query = update.callback_query
    await query.answer()

    action = query.data
    lang = context.user_data.get('lang', 'uk')

    if action == 'confirm_ts':
        context.user_data['status'] = 'creating_task'
        await query.edit_message_text(text=t('creating_task', lang))

        # Create task in Worksection
        project_id = context.user_data.get('project_id')
        description = context.user_data.get('description', '')
        priority = context.user_data.get('priority', 5)
        ws_text = _build_ws_text(context)
        title = context.user_data.get('task_title', description[:100])
        deadline = context.user_data.get('deadline', '')
        file_ids = context.user_data.get('file_ids', [])

        # Download files from Telegram
        attach_files = {}
        temp_paths = []
        if file_ids:
            bot = context.bot
            for idx, (file_id, filename) in enumerate(file_ids):
                try:
                    tg_file = await bot.get_file(file_id)
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    await tg_file.download_to_drive(temp_path)
                    attach_files[f'attach[{idx}]'] = (filename, open(temp_path, 'rb'))
                    temp_paths.append(temp_path)
                except Exception as e:
                    logger.error(f"Failed to download file {filename}: {e}")

        if project_id:
            result = ws_api.post_task(
                id_project=project_id,
                title=title,
                text=ws_text,
                priority=priority,
                dateend=deadline,
                files=attach_files if attach_files else None,
            )

            # Close file handles and cleanup
            for key, val in attach_files.items():
                val[1].close()
            for path in temp_paths:
                try:
                    os.remove(path)
                except:
                    pass

            if result.get('status') == 'ok':
                task_data = result.get('data', {})
                task_link = task_data.get('page', '')
                priority_label = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['en']).get(priority, '')
                project_name = context.user_data.get('projects_map', {}).get(str(project_id), '')

                context.user_data['status'] = 'completed'
                await query.message.reply_text(
                    t('task_created', lang, link=task_link, priority=priority_label, project=project_name)
                )
            else:
                error_msg = result.get('message', 'Unknown error')
                await query.message.reply_text(
                    t('task_error', lang, error=error_msg)
                )
        else:
            # No project selected — save locally as fallback
            ts_text = context.user_data.get('ts_text', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'ts_{timestamp}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(ts_text)

            context.user_data['status'] = 'completed'
            await query.message.reply_text(t('ts_confirmed', lang))

    elif action == 'edit_ts':
        context.user_data['status'] = 'waiting_description'
        await query.edit_message_text(text=t('start', lang))

    elif action == 'cancel_ts':
        context.user_data['status'] = 'idle'
        await query.edit_message_text(text=t('ts_cancelled', lang))


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file and photo uploads"""
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
        # Photos come as array of sizes, take the largest
        photo = update.message.photo[-1]
        filename = f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
        file_id = photo.file_id

    if filename:
        context.user_data['files'].append(filename)
        if file_id:
            context.user_data['file_ids'].append((file_id, filename))
        await update.message.reply_text(
            t('file_uploaded', lang, filename=filename)
        )

        # If photo/file has caption, treat it as description
        caption = update.message.caption
        if caption and context.user_data.get('status') == 'waiting_description':
            context.user_data['description'] = caption
            await ask_priority(update, context, lang)


def main() -> None:
    """Start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern='^lang_'))
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern='^category_'))
    application.add_handler(CallbackQueryHandler(handle_priority_selection, pattern='^priority_'))
    application.add_handler(CallbackQueryHandler(handle_project_selection, pattern='^project_'))
    application.add_handler(CallbackQueryHandler(handle_ts_confirmation, pattern='^(confirm_ts|edit_ts|cancel_ts)$'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(MessageHandler(filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
