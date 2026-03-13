"""
Odoo Analyst AI Agent
Uses OpenAI GPT-4 for intelligent task analysis and TS generation.
Uses Whisper for voice message transcription.
"""

import os
import logging
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_PROMPT = """You are a senior Odoo ERP analyst and solution architect. Your role is to help users create detailed, developer-ready technical specifications for Odoo tasks.

Your expertise:
- Odoo modules: Sales, Purchase, Inventory, Accounting, CRM, HR, Manufacturing, Website, eCommerce, Project, Helpdesk
- Odoo architecture: models, views (form/tree/kanban), actions, security rules, wizards, reports, scheduled actions, API/XML-RPC
- Python/OWL/QWeb development for Odoo
- PostgreSQL database structure
- Odoo customization best practices

When analyzing a user's request:
1. Identify which Odoo module(s) are involved
2. Determine if this is a bug fix, new feature, customization, or configuration
3. Think about what a developer needs to know to implement this

When asking clarifying questions:
- Ask 2-3 focused, specific questions
- Ask about: affected module, current behavior vs expected, user roles, data flow, integrations
- Do NOT ask obvious questions
- Be concise

When generating a technical specification:
- Write a clear title
- Describe current state and desired state
- List specific Odoo models/views affected
- Define acceptance criteria
- Note any risks or dependencies
- Structure it so a developer can start working immediately

IMPORTANT: Respond in the SAME LANGUAGE as the user's message."""


def transcribe_voice(audio_path: str) -> str:
    """Transcribe voice message using OpenAI Whisper"""
    try:
        with open(audio_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ''


def analyze_task(description: str, lang: str = 'uk') -> str:
    """Analyze user's task description and generate clarifying questions"""
    lang_instructions = {
        'uk': 'Відповідай українською.',
        'en': 'Respond in English.',
        'ru': 'Отвечай на русском.',
        'pl': 'Odpowiadaj po polsku.',
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + lang_instructions.get(lang, '')},
                {"role": "user", "content": f"User described this task:\n\n{description}\n\nAsk 2-3 clarifying questions to create a detailed technical specification. Be concise."}
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI analyze failed: {e}")
        return ''


def generate_specification(description: str, qa_history: list, lang: str = 'uk') -> dict:
    """Generate a detailed technical specification based on description and Q&A"""
    lang_instructions = {
        'uk': 'Відповідай українською.',
        'en': 'Respond in English.',
        'ru': 'Отвечай на русском.',
        'pl': 'Odpowiadaj po polsku.',
    }

    # Build conversation context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + lang_instructions.get(lang, '')},
        {"role": "user", "content": f"Initial task description:\n\n{description}"},
    ]

    for q, a in qa_history:
        messages.append({"role": "assistant", "content": q})
        messages.append({"role": "user", "content": a})

    messages.append({
        "role": "user",
        "content": """Now generate a complete technical specification for a developer.

Format:
TITLE: [short task title]

DESCRIPTION:
[detailed description of what needs to be done]

AFFECTED MODULES:
[list of Odoo modules]

CURRENT BEHAVIOR:
[what happens now]

EXPECTED BEHAVIOR:
[what should happen after implementation]

TECHNICAL DETAILS:
[models, views, fields, methods that need changes]

ACCEPTANCE CRITERIA:
[numbered list of criteria to verify the task is complete]

RISKS/DEPENDENCIES:
[any risks or dependencies]"""
    })

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1500,
            temperature=0.3,
        )
        content = response.choices[0].message.content

        # Extract title from response
        title = ''
        for line in content.split('\n'):
            if line.strip().upper().startswith('TITLE:') or line.strip().upper().startswith('НАЗВА:') or line.strip().upper().startswith('НАЗВАНИЕ:') or line.strip().upper().startswith('TYTUŁ:'):
                title = line.split(':', 1)[1].strip()
                break

        if not title:
            title = description[:100]

        return {
            'title': title,
            'text': content,
        }
    except Exception as e:
        logger.error(f"OpenAI generate spec failed: {e}")
        return {
            'title': description[:100],
            'text': description,
        }
