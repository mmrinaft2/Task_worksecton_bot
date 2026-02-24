# Odoo Task Management Bot 🤖

A Telegram bot that helps you create detailed technical specifications (ТЗ) for Odoo tasks.

## Features 🎯

✅ **Multi-language support** (Ukrainian, English, Russian)
✅ **Category selection** (Bug, Feature, Improvement, Support)
✅ **Context-aware questions** based on task category
✅ **File uploads** for attachments
✅ **Auto-generated specifications** in structured format
✅ **User confirmation** before finalizing

## How It Works

1. **User describes the task** → Bot detects language
2. **Select category** → Bug, Feature, Improvement, or Support
3. **Answer questions** → Bot asks 3-5 context-specific questions
4. **Upload files** (optional) → Attach screenshots, documents
5. **Review TS** → Check generated specification
6. **Confirm** → Accept and save, or edit

## Setup 🚀

### Prerequisites
- Python 3.9+
- Telegram account
- BotFather bot to create a Telegram bot

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/mmrinaft2/Task_worksecton_bot.git
cd Task_worksecton_bot
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create Telegram bot**
   - Open Telegram and search for **@BotFather**
   - Send `/newbot` command
   - Follow instructions to get your **token**

5. **Configure environment**
   - Copy `env.example` to `.env`
   - Replace `your_bot_token_here` with your actual token

```bash
cp env.example .env
```

6. **Run the bot**
```bash
python main.py
```

## Configuration 🔧

Edit `.env` file with your tokens:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmnoPQRstuvWXYZabcdef

# Optional (Phase 2)
WORKSECTION_API_TOKEN=your_token
WORKSECTION_PROJECT_ID=12345
```

## Usage Example 💬

**User:** "I need to add a filter by date in the Sales module"

**Bot:** 
```
🎯 Select a category:
[✨ Feature]  [⚡ Improvement]  [🐛 Bug]  [🆘 Support]
```

**User clicks:** ✨ Feature

**Bot:**
```
✨ What is the goal of this feature?
(answer or type "skip")
```

**User:** "Allow users to filter sales by date range"

**Bot:** (asks 3 more questions)

**User:** (answers or skips)

**Bot:** (generates beautiful TS)

```
═══════════════════════════════════════
          ТЕХНІЧНЕ ЗАВДАННЯ
═══════════════════════════════════════

📌 КАТЕГОРІЯ: FEATURE
📝 ОПИС: Add filter by date in Sales module
...
═══════════════════════════════════════
```

**Bot:** "Все добре? ✅ Так | ✏️ Редагувати | ❌ Скасувати"

## Project Structure 📁

```
Task_worksecton_bot/
├── main.py              # Main bot logic
├── requirements.txt     # Python dependencies
├── env.example          # Environment variables template
├── .env                 # (Create from env.example)
├── README.md            # This file
└── .gitignore           # Git ignore rules
```

## Phases 📈

### Phase 1 (Current) ✅
- Bot creates specifications locally
- Multi-language support
- Category-specific questions
- File uploads

### Phase 2 (Next)
- WorkSection integration
- Odoo direct integration
- Auto-create tasks in WorkSection

## Troubleshooting 🛠️

**Bot doesn't respond?**
- Check if `TELEGRAM_BOT_TOKEN` is correct
- Restart the bot

**Language detection not working?**
- Default is Ukrainian. Edit `main.py` line with `get_language()`

**Files not uploading?**
- Ensure bot has permissions
- Check file size limits

## Contributing 🤝

Feel free to fork, improve, and suggest features!

## License 📄

MIT License - feel free to use this project

---

Made with ❤️ by Марина & Шершень 🐝
