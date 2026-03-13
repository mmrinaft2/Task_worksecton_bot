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
from ai_agent import get_clarifying_questions, generate_spec

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
}

DAY_NAMES = {
    'uk': ['Пн','Вт','Ср','Чт','Пт','Сб','Нд'],
    'en': ['Mo','Tu','We','Th','Fr','Sa','Su'],
    'ru': ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'],
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
    skip_text = {'uk': '⏭ Пропустити', 'en': '⏭ Skip', 'ru': '⏭ Пропустить'}.get(lang, '⏭ Пропустити')
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
                          'ru': f'📅 Срок: {deadline_str}'}.get(lang, f'📅 {deadline_str}')
        await query.edit_message_text(text=deadline_label)

        # Proceed to generate TS
        await generate_ts_after_deadline(query.message, context, lang)

    elif data == 'cal_skip':
        context.user_data['deadline'] = ''
        skip_label = {'uk': '📅 Без терміну', 'en': '📅 No deadline', 'ru': '📅 Без срока'}.get(lang, '📅 Без терміну')
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
        # Map language codes to our supported languages
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
    lang = 'uk'  # Default to Ukrainian
    
    context.user_data['user_id'] = user_id
    context.user_data['lang'] = lang
    context.user_data['status'] = 'waiting_description'
    context.user_data['category'] = None
    context.user_data['description'] = None
    context.user_data['answers'] = {}
    context.user_data['files'] = []
    context.user_data['file_ids'] = []
    context.user_data['links'] = []
    context.user_data['priority'] = 5
    context.user_data['deadline'] = ''
    
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
    
    lang = context.user_data.get('lang', 'uk')
    status = context.user_data.get('status', 'waiting_description')
    
    # Detect language from message
    detected_lang = get_language(message_text)
    if detected_lang in ['uk', 'en', 'ru']:
        context.user_data['lang'] = detected_lang
        lang = detected_lang
    
    if status == 'waiting_description':
        _reset_task_data(context)
        context.user_data['description'] = message_text
        await ask_category(update, context, lang)
    
    elif status == 'category_selected':
        # Skip category re-selection, just wait for questions
        await ask_questions(update, context)
    
    elif status == 'answering_questions':
        question_index = context.user_data.get('current_question_index', 0)
        if message_text.lower() in ['пропустити', 'skip', 'пропустить']:
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
    """Handle category selection — ask AI for smart questions"""
    query = update.callback_query
    await query.answer()

    category = query.data.split('_')[1]
    context.user_data['category'] = category
    context.user_data['current_question_index'] = 0
    context.user_data['status'] = 'answering_questions'

    lang = context.user_data.get('lang', 'uk')
    description = context.user_data.get('description', '')

    thinking_text = {
        'uk': '🤔 Аналізую задачу як Odoo-архітектор...',
        'en': '🤔 Analyzing task as Odoo architect...',
        'ru': '🤔 Анализирую задачу как Odoo-архитектор...',
    }.get(lang, '🤔 Аналізую...')

    await query.edit_message_text(text=thinking_text)

    # Get AI-generated questions
    ai_questions = await get_clarifying_questions(description, category, lang)

    # Fallback to static questions if AI fails
    if not ai_questions:
        ai_questions = CATEGORY_QUESTIONS.get(category, {}).get(lang, [])

    context.user_data['ai_questions'] = ai_questions

    if ai_questions:
        provide_answer = t('provide_answer', lang)
        await query.edit_message_text(
            text=t('questions_for_category', lang) + '\n\n' +
                 ai_questions[0] + '\n\n' +
                 provide_answer
        )
    else:
        await generate_ts(update, context, lang)


async def ask_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask category-specific questions"""
    lang = context.user_data.get('lang', 'uk')
    await ask_category(update, context, lang)


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
            link_text = f"\n🔗 {task_link}" if task_link else ""
            await query.message.reply_text(
                f"✅ Задачу створено у Worksection!\n📂 Проект: {WS_PROJECT_NAME}{link_text}\n\nНова задача? Просто напиши опис."
            )
        else:
            error_msg = result.get('message', 'Unknown error')
            await query.message.reply_text(
                f"❌ Помилка при створенні задачі: {error_msg}"
            )
        
    elif action == 'edit_ts':
        await query.answer()
        _reset_task_data(context)
        context.user_data['status'] = 'waiting_description'
        await query.edit_message_text(text=t('start', lang))

    elif action == 'cancel_ts':
        await query.answer()
        _reset_task_data(context)
        context.user_data['status'] = 'idle'
        await query.edit_message_text(text=t('ts_cancelled', lang))


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
        context.user_data['files'].append(filename)
        if file_id:
            context.user_data['file_ids'].append((file_id, filename))
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
    application.add_handler(CallbackQueryHandler(handle_calendar, pattern='^cal_'))
    application.add_handler(CallbackQueryHandler(handle_ts_confirmation, pattern='^(confirm|edit|cancel)_'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(MessageHandler(filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.VIDEO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
