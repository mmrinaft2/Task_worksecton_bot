#!/usr/bin/env python3
"""
Odoo Task Management Bot for Telegram
Converts user descriptions into well-structured technical specifications
and creates tasks in Worksection
"""

import os
import json
import logging
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
        'task_created': '✅ Задачу створено у Worksection!\n\n🔗 {link}\n📌 Пріоритет: {priority}',
        'task_error': '❌ Помилка при створенні задачі: {error}',
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
        'task_created': '✅ Task created in Worksection!\n\n🔗 {link}\n📌 Priority: {priority}',
        'task_error': '❌ Error creating task: {error}',
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
        'task_created': '✅ Задача создана в Worksection!\n\n🔗 {link}\n📌 Приоритет: {priority}',
        'task_error': '❌ Ошибка при создании задачи: {error}',
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


def get_language(user_text: str) -> str:
    """Detect user's language"""
    try:
        lang = detect(user_text)
        lang_map = {'uk': 'uk', 'en': 'en', 'ru': 'ru'}
        return lang_map.get(lang, 'en')
    except:
        return 'en'


def t(key: str, lang: str, **kwargs) -> str:
    """Get translated string"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    user_id = update.effective_user.id
    lang = 'uk'

    context.user_data['user_id'] = user_id
    context.user_data['lang'] = lang
    context.user_data['status'] = 'waiting_description'
    context.user_data['category'] = None
    context.user_data['description'] = None
    context.user_data['answers'] = {}
    context.user_data['files'] = []
    context.user_data['priority'] = None
    context.user_data['project_id'] = None

    await update.message.reply_text(t('start', lang))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages"""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Initialize user context if not exists
    if 'lang' not in context.user_data:
        context.user_data['lang'] = get_language(message_text)
        context.user_data['status'] = 'waiting_description'
        context.user_data['user_id'] = user_id
        context.user_data['description'] = None
        context.user_data['answers'] = {}
        context.user_data['category'] = None
        context.user_data['files'] = []
        context.user_data['priority'] = None
        context.user_data['project_id'] = None

    lang = context.user_data.get('lang', 'uk')
    status = context.user_data.get('status', 'waiting_description')

    # Detect language from message
    detected_lang = get_language(message_text)
    if detected_lang in ['uk', 'en', 'ru']:
        context.user_data['lang'] = detected_lang
        lang = detected_lang

    if status == 'waiting_description':
        context.user_data['description'] = message_text
        await ask_category(update, context, lang)

    elif status == 'category_selected':
        await ask_questions(update, context)

    elif status == 'answering_questions':
        question_index = context.user_data.get('current_question_index', 0)
        if message_text.lower() in ['пропустити', 'skip', 'пропустить']:
            context.user_data['answers'][question_index] = None
        else:
            context.user_data['answers'][question_index] = message_text

        question_index += 1
        category = context.user_data.get('category')
        questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])

        if question_index < len(questions):
            context.user_data['current_question_index'] = question_index
            await update.message.reply_text(
                f"{questions[question_index]}\n\n{t('provide_answer', lang)}"
            )
        else:
            # All questions answered -> ask priority
            await ask_priority(update, context, lang)


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

    # Next step: select project
    await ask_project(query, context, lang)


async def ask_project(query, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Fetch projects from Worksection and ask user to select one"""
    projects = ws_api.get_projects()

    if not projects:
        await query.message.reply_text(t('no_projects', lang))
        # Fallback: generate TS without Worksection
        await generate_ts_from_query(query, context, lang)
        return

    keyboard = []
    # Store projects mapping for later use
    context.user_data['projects_map'] = {}
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', f'Project {project_id}')
        context.user_data['projects_map'][str(project_id)] = project_name
        keyboard.append([
            InlineKeyboardButton(project_name, callback_data=f'project_{project_id}')
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['status'] = 'selecting_project'
    await query.message.reply_text(t('select_project', lang), reply_markup=reply_markup)


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


async def generate_ts(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Generate technical specification (called from message handler)"""
    await update.message.reply_text(t('generating_ts', lang))
    ts_text = _build_ts_text(context, lang)
    context.user_data['ts_text'] = ts_text
    context.user_data['status'] = 'confirming_ts'

    await update.message.reply_text(t('ts_generated', lang) + ts_text)
    await _send_confirmation_buttons(update.message, context, lang)


async def generate_ts_from_query(query, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Generate technical specification (called from callback query)"""
    await query.message.reply_text(t('generating_ts', lang))
    ts_text = _build_ts_text(context, lang)
    context.user_data['ts_text'] = ts_text
    context.user_data['status'] = 'confirming_ts'

    await query.message.reply_text(t('ts_generated', lang) + ts_text)
    await _send_confirmation_buttons(query.message, context, lang)


def _build_ts_text(context: ContextTypes.DEFAULT_TYPE, lang: str) -> str:
    """Build the TS text from user data"""
    description = context.user_data.get('description', '')
    category = context.user_data.get('category', 'feature')
    answers = context.user_data.get('answers', {})
    files = context.user_data.get('files', [])
    priority = context.user_data.get('priority', 5)
    priority_label = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['en']).get(priority, '')

    ts_text = f"""═══════════════════════════════════════
          ТЕХНІЧНЕ ЗАВДАННЯ
═══════════════════════════════════════

📌 КАТЕГОРІЯ: {category.upper()}
🔥 ПРІОРИТЕТ: {priority_label} ({priority}/10)
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
    return ts_text


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
        category = context.user_data.get('category', 'feature')
        priority = context.user_data.get('priority', 5)
        ts_text = context.user_data.get('ts_text', '')

        # Title: first 100 chars of description
        title = description[:100] if len(description) > 100 else description

        if project_id:
            result = ws_api.post_task(
                id_project=project_id,
                title=title,
                text=ts_text,
                priority=priority,
                tags=category,
            )

            if result.get('status') == 'ok':
                task_data = result.get('data', {})
                task_link = task_data.get('page', '')
                priority_label = PRIORITY_LABELS.get(lang, PRIORITY_LABELS['en']).get(priority, '')

                context.user_data['status'] = 'completed'
                await query.message.reply_text(
                    t('task_created', lang, link=task_link, priority=priority_label)
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
    """Handle file uploads"""
    lang = context.user_data.get('lang', 'uk')

    if update.message.document:
        file = update.message.document
        filename = file.file_name

        if 'files' not in context.user_data:
            context.user_data['files'] = []

        context.user_data['files'].append(filename)
        await update.message.reply_text(
            t('file_uploaded', lang, filename=filename)
        )


def main() -> None:
    """Start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern='^category_'))
    application.add_handler(CallbackQueryHandler(handle_priority_selection, pattern='^priority_'))
    application.add_handler(CallbackQueryHandler(handle_project_selection, pattern='^project_'))
    application.add_handler(CallbackQueryHandler(handle_ts_confirmation, pattern='^(confirm_ts|edit_ts|cancel_ts)$'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
