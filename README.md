# Chess Club Management System

## Overview

I built this project to keep chess club members, matches, and rankings in one place. It is a Flask app backed by SQLite that makes it easy to manage players, record games, and view club standings without chasing paper notes.

The main flow in this version focuses on:

- leaderboard and ranking display
- match recording and status updates
- match history and club outcome summaries
- player search, ranking filters, and avatar support

The app also includes optional auth and profile routes in the code, but those are disabled by default unless `CHESS_AUTH_PHASE_ENABLED=true`.

## What is included

- `app.py`: Flask routes, database access, file uploads, and template rendering
- `helpers.py`: helper utilities for avatars, uploads, and auth decorators
- `templates/`: HTML templates for leaderboard, members, matches, history, auth, and error pages
- `static/`: CSS, JavaScript, and `uploads/` for avatar images
- `db/ChessAdmin.sqlite3`: default SQLite database for the app
- `tests/test_phase1_hardening.py`: 11 tests covering core member and match behavior
- `requirements.txt`: Flask and python-dotenv dependencies

## Key features

- leaderboard with rank, points, matches played, and win ratio
- match recording page with result tracking
- history page with edit/delete actions for recorded matches
- avatar upload support for players and users
- charts for top players, ranking trends, and match outcomes
- search and table filter controls for faster navigation

## Project structure

ChessWBA/
├── app.py
├── helpers.py
├── README.md
├── requirements.txt
├── db/
│   └── ChessAdmin.sqlite3
├── static/
│   ├── styles.css
│   ├── css/
│   ├── js/
│   └── uploads/
├── templates/
│   ├── index.html
│   ├── members.html
│   ├── match.html
│   ├── history.html
│   ├── login.html
│   ├── register.html
│   ├── edit_profile.html
│   ├── 404.html
│   └── 500.html
└── tests/
    └── test_phase1_hardening.py

Remove generated files before submission: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `session_data/`, and `node_modules/` are not required.

## Run locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Use the included database

The app looks for `./db/ChessAdmin.sqlite3` by default. If you want to use a different database, set:

```powershell
$env:CHESS_DB_PATH = "C:\path\to\ChessAdmin.sqlite3"
```

### 3. Start the app

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### 4. Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Or, if you prefer pytest:

```bash
python -m pytest tests/test_phase1_hardening.py -q
```

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `CHESS_DB_PATH` | Path to the SQLite database file | `./db/ChessAdmin.sqlite3` |
| `CHESS_SECRET_KEY` | Flask secret key | `chess-club-secret-key-2024` |
| `CHESS_AUTH_PHASE_ENABLED` | Enable login/register/profile routes (`true`/`false`) | `false` |
| `CHESS_MAX_UPLOAD_MB` | Maximum avatar upload size in megabytes | `5` |

## Notes

- I kept this app lightweight so the club workflow stays easy to follow.
- The included database is ready to use, so the app works out of the box.
- Authentication and profile pages are available in the codebase, but the normal demo path is members, matches, rankings, and history.
- If you want to use a `.env` workflow with the Flask CLI, python-dotenv is included in the dependencies.
