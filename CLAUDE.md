# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** — a personal expense tracking web app built with Flask and SQLite. This is a step-by-step learning project; some features are stubs awaiting implementation.

## Commands

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_auth.py
```

## Architecture

### Backend
- **`app.py`** — Single file containing the Flask app and all route definitions. All new routes go here.
- **`database/db.py`** — SQLite helper module. Must expose three functions:
  - `get_db()` — returns a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`
  - `init_db()` — creates tables using `CREATE TABLE IF NOT EXISTS`
  - `seed_db()` — inserts sample data for development
- The SQLite database file is `expense_tracker.db` (gitignored).

### Templates
Jinja2 templates in `templates/`. All pages extend `templates/base.html`, which provides the navbar (`/login`, `/register`) and footer (Terms/Privacy links).

### Static Assets
- `static/css/style.css` — global styles shared across all pages
- `static/css/landing.css` — landing page-specific styles
- `static/js/main.js` — global vanilla JS (no frameworks; keep all JS vanilla)

## Planned Routes (stubs in `app.py`)
| Route | Status |
|---|---|
| `GET /` | Done |
| `GET /login`, `GET /register` | Done (no auth logic yet) |
| `GET /terms`, `GET /privacy` | Done |
| `GET /logout` | Stub — Step 3 |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET/POST /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

## Key Constraints
- No JavaScript frameworks — vanilla JS only.
- No CSS frameworks — custom CSS only.
- `file.txt` contains historical task prompts used to build the project; not application code.
