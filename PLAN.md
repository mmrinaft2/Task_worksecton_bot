# Plan: Telegram Bot + Worksection Integration

## Overview

Integrating the Telegram bot with Worksection API to automatically create tasks when the user confirms a generated technical specification (TS).

---

## Worksection API

- **Base URL:** `https://{account}.worksection.com/api/admin/v2/`
- **Auth:** MD5 hash — `md5(query_params + api_key)`
- **Rate limit:** 1 request/sec
- **Response:** `{"status": "ok", "data": {...}}`
- **API key:** Account > API > "Show API key"

---

## Phase 1 — Base Integration

### 1.1. Worksection API Client

Create `worksection_api.py` module:
- Authentication via MD5 hash
- Environment variables: `WORKSECTION_API_KEY`, `WORKSECTION_ACCOUNT_URL`
- Methods:
  - `get_projects()` — list of active projects
  - `post_task()` — create task
  - `get_task_tags()` — get available tags

### 1.2. Priority Selection (Urgency)

Add a new step in the bot flow — priority selection after category:

| Button | Priority Value | Description |
|--------|---------------|-------------|
| Low | 1-2 | Not urgent, can wait |
| Normal | 3-4 | Standard priority |
| Medium | 5-6 | Important |
| High | 7-8 | Urgent |
| Critical | 9-10 | Requires immediate attention |
| Suspended | 0 | On hold |

Worksection supports priority **0-10** (0 = suspended, 10 = highest).

### 1.3. Project Selection

- Call `get_projects(filter=active)` to fetch active projects
- Display inline buttons for the user to choose a project
- Save selected `id_project` in user context

### 1.4. Task Creation on Confirmation

When user clicks "Confirm":
- Call `post_task` with parameters:
  - `id_project` — selected project
  - `title` — short task description
  - `text` — full generated TS
  - `priority` — selected priority
  - `tags` — category (Bug/Feature/Improvement/Support)
- Send task link back to the user

### 1.5. Updated Bot Flow

```
/start
  -> User describes the task
  -> Select category (Bug / Feature / Improvement / Support)
  -> Answer 3-4 questions
  -> Select priority (urgency level)
  -> Select project (from Worksection)
  -> Review generated TS
  -> Confirm -> CREATE TASK IN WORKSECTION
  -> Bot sends task link
```

---

## Phase 2 — Extended Features

### 2.1. File Attachments

- Files uploaded to the bot are sent via `attach[n]` parameter in `post_task`
- Download files from Telegram, then upload to Worksection

### 2.2. Assignee Selection

- Fetch project members via API
- Display inline buttons to select the task assignee (`email_user_to`)

### 2.3. Deadlines

- Add a step to set `dateend` (deadline) via date picker or text input
- Format: DD.MM.YYYY

### 2.4. Tags

- Fetch available tags via `get_task_tags`
- Allow user to add additional tags beyond the category

---

## Phase 3 — Advanced Capabilities

| Feature | API Method | Description |
|---------|-----------|-------------|
| View my tasks | `get_all_tasks` | `/mytasks` command — list assigned tasks |
| Close task | `complete_task` | Close tasks from Telegram |
| Search tasks | `search_tasks` | Search tasks by keywords |
| Add comments | `post_comment` | Post updates to existing tasks |
| Status tags | `update_task_tags` | Set statuses (In Progress, Done, Testing) |
| Time tracking | Timers API | Start/stop timers for tasks |
| Cost logging | Costs API | Log time/money expenses |
| Event history | `get_events` | Monitor project changes |
| Webhooks | Webhooks API | Receive notifications in Telegram when tasks change |
| Project folders | `get_project_groups` | Navigate project structure |

---

## Environment Variables

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Worksection
WORKSECTION_API_KEY=your_api_key
WORKSECTION_ACCOUNT_URL=https://youraccount.worksection.com
```

---

## API Reference

| Endpoint | Method | Required Params |
|----------|--------|----------------|
| `get_projects` | GET | — (optional: `filter`) |
| `get_project` | GET | `id_project` |
| `post_task` | POST | `id_project`, `title` |
| `update_task` | POST | `id_task` |
| `complete_task` | POST | `id_task` |
| `reopen_task` | POST | `id_task` |
| `search_tasks` | GET | `filter` (text query) |
| `get_task_tags` | GET | — |
| `update_task_tags` | POST | `id_task`, `plus`/`minus` |
| `post_comment` | POST | `id_task`, `text` or `todo[]` |
| `get_comments` | GET | `id_task` |
| `get_files` | GET | `id_project` or `id_task` |

### post_task Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id_project` | Yes | Project ID |
| `title` | Yes | Task name |
| `text` | No | Task description |
| `email_user_to` | No | Assignee email (or `ANY` / `NOONE`) |
| `priority` | No | 0-10 |
| `datestart` | No | DD.MM.YYYY |
| `dateend` | No | DD.MM.YYYY |
| `tags` | No | Comma-separated tag names or IDs |
| `todo[]` | No | Checklist items |
| `attach[n]` | No | File attachments |
| `max_time` | No | Planned time |
| `max_money` | No | Planned budget |
| `hidden` | No | Restricted visibility (emails) |
| `subscribe` | No | Subscriber emails |
| `mention` | No | Mentioned user emails |

---

## Implementation Order

1. `worksection_api.py` — API client module
2. Priority selection step in bot flow
3. Project selection step (list from API)
4. Task creation in Worksection on confirmation
5. File attachments
6. Extended features (comments, task list, etc.)
