import os
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_PROMPT = """You are a senior Odoo architect and business analyst with 10+ years of experience.
You work at a software company and help clarify tasks before passing them to developers.

Your expertise includes:
- Odoo modules: Sale, Purchase, Inventory, Accounting, CRM, HR, Manufacturing, Project
- Odoo technical stack: ORM, computed fields, onchange, wizards, reports, QWeb, XML-RPC/JSON-RPC
- Business process analysis and requirements gathering
- Writing clear, actionable technical specifications

When asking questions: be specific, technical, and focused on what developers need to know.
When writing specs: be precise, reference exact Odoo models/fields/methods where applicable.
"""


async def analyze_and_get_questions(description: str, lang: str) -> tuple:
    """
    Analyze task description: auto-detect category and generate 2-3 clarifying questions.
    Returns (category, questions_list)
    """

    lang_map = {
        'uk': 'Відповідай виключно українською мовою.',
        'en': 'Respond exclusively in English.',
        'ru': 'Отвечай исключительно на русском языке.',
        'pl': 'Odpowiadaj wyłącznie po polsku.',
    }
    lang_instruction = lang_map.get(lang, lang_map['uk'])

    prompt = f"""{lang_instruction}

Ти — Odoo-архітектор. Замовник описав задачу:

"{description}"

1. Визнач категорію задачі. Варіанти: bug, feature, improvement, support
2. Задай 2-3 найважливіших уточнюючих питання, відповіді на які допоможуть програмісту точно зрозуміти що робити.

Вимоги до питань:
- Конкретні та технічні (стосуються Odoo, бізнес-логіки, або UX)
- Не запитуй очевидне з опису
- Фокусуйся на найкритичнішому: які модулі/моделі зачеплені, які edge cases, хто користувач

Формат відповіді (СТРОГО дотримуйся):
CATEGORY: <одне слово: bug/feature/improvement/support>
QUESTIONS:
<питання 1>
<питання 2>
<питання 3>"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()

        # Parse category
        category = 'feature'
        for line in text.split('\n'):
            if line.strip().upper().startswith('CATEGORY:'):
                cat = line.split(':', 1)[1].strip().lower()
                if cat in ('bug', 'feature', 'improvement', 'support'):
                    category = cat
                break

        # Parse questions
        questions = []
        in_questions = False
        for line in text.split('\n'):
            if line.strip().upper().startswith('QUESTIONS:'):
                in_questions = True
                continue
            if in_questions and line.strip() and len(line.strip()) > 10:
                questions.append(line.strip())

        return category, questions[:3]
    except Exception as e:
        logger.error(f"AI analyze error: {e}")
        return 'feature', []


async def generate_spec(
    description: str,
    category: str,
    questions: list,
    answers: dict,
    deadline: str,
    lang: str
) -> tuple:
    """
    Generate full technical specification.
    Returns (title, spec_text)
    """

    lang_map = {
        'uk': 'Склади ТЗ українською мовою.',
        'en': 'Write the specification in English.',
        'ru': 'Составь ТЗ на русском языке.',
        'pl': 'Napisz specyfikację po polsku.',
    }
    lang_instruction = lang_map.get(lang, lang_map['uk'])

    # Build Q&A context
    qa_block = ""
    for i, q in enumerate(questions):
        ans = answers.get(i)
        if ans:
            qa_block += f"\nПитання: {q}\nВідповідь: {ans}\n"

    deadline_block = f"\nТермін виконання: {deadline}" if deadline else ""

    prompt = f"""{lang_instruction}

Ти — старший Odoo-архітектор. Склади повне технічне завдання для програміста на основі наданої інформації.

--- ВХІДНІ ДАНІ ---
Тип задачі: {category.upper()}
Опис від замовника: {description}{deadline_block}

Уточнення:{qa_block if qa_block else ' (не надано)'}
--- КІНЕЦЬ ВХІДНИХ ДАНИХ ---

Склади ТЗ у такому форматі:

**НАЗВА:** [коротка назва задачі, до 80 символів]

**МЕТА:**
[1-2 речення: яку бізнес-проблему вирішує ця задача]

**ТЕХНІЧНИЙ ОПИС:**
[Детально що потрібно зробити в Odoo: які моделі змінити/створити, які поля додати, яку бізнес-логіку реалізувати. Посилайся на конкретні Odoo-моделі (наприклад: sale.order, res.partner, stock.move)]

**КРОКИ РЕАЛІЗАЦІЇ:**
1. [крок]
2. [крок]
3. [крок]
...

**КРИТЕРІЇ ПРИЙНЯТТЯ:**
- [що має працювати після завершення]
- [edge cases які мають бути оброблені]

Будь технічним та конкретним. Програміст повинен мати все необхідне для початку роботи."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1800,
            temperature=0.4
        )
        spec_text = response.choices[0].message.content.strip()

        # Extract title from spec
        title = description[:80].split('.')[0].split('\n')[0].strip()
        for line in spec_text.split('\n'):
            if '**НАЗВА:**' in line or '**NAME:**' in line or '**НАЗВАНИЕ:**' in line or '**TITLE:**' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    extracted = parts[1].strip().strip('*').strip()
                    if extracted:
                        title = extracted[:100]
                break

        return title, spec_text

    except Exception as e:
        logger.error(f"AI spec generation error: {e}")
        # Fallback: return simple spec
        fallback = f"Категорія: {category.upper()}\n\nОпис: {description}"
        if qa_block:
            fallback += f"\n\nУточнення:{qa_block}"
        return description[:80], fallback
