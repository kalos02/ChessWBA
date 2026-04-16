# Chess Club Management System

## Video Demo

To be added.

## Description

I built this project to solve a simple but common problem in chess clubs: results are often tracked in scattered notes, and rankings become hard to trust after many matches. This app keeps everything in one place so it is easier to manage players, record games, and show fair rankings.

Chess Club Management System is a Flask web app with a SQLite database. Players are managed through the system interface, and the dashboard shows current standings and match statistics. The goal of the app is not to be a huge enterprise platform, but a practical tool that a student club can actually use.

For this final project version, the active flow focuses on members, rankings, match recording, and history. Authentication pages are reserved for future work and are not part of the current demo navigation.

The dashboard is the center of the project. It shows:

- total members
- total matches
- your current rank
- current top player

It also has charts so the data is easier to understand quickly:

- Top Players by Points
- Ranking Trend (simulated)
- All-Time Match Outcomes (Club Overview)

These charts are intentionally simple. I wanted them to be useful during a demo and easy to explain, not overly complicated. The ranking trend chart is simulated from current ranks for readability and demo storytelling; it is not historical rank tracking.

The app focuses on ranking and performance tracking. Players are listed in clear tables, and each player's details can be viewed from the members and ranking pages. The ranking table and points table are readable and include points, matches played, and win ratio. To make the dashboard practical, I added:

- sorting for useful columns
- search by player name
- top filters (All, Top 5, Top 10)

This makes it easier to find players during meetings without scrolling through everything.

The ranking flow is based on match results. A user can record a match from the match page, and the app updates player statistics. That keeps rankings and performance values tied to real recorded results. The history page helps users check past activity and verify what happened.

Project structure is straightforward:

- app.py: Flask routes, request handling, template rendering, and database queries
- helpers.py: shared helper functions used by routes/templates
- templates/: all HTML pages (dashboard, members, match, history, player details, errors)
- login/register/edit_profile templates are kept for future authentication work and are not used in the current top navigation flow
- static/: styles and uploaded images
- ChessAdmin.sqlite3: database with users, players, and matches
- requirements.txt: dependencies needed to run the app

I used Flask because it is lightweight and easy to reason about in a CS50 final project. It lets me keep backend logic readable and route-by-route. I used SQLite because setup is simple, local, and perfect for a student project demo. I used Jinja templates because they connect cleanly with Flask and keep the frontend organized without adding heavy frameworks.

One design choice I focused on was clarity over complexity. I moved the app to a clean top navigation layout and removed old sidebar structure so pages feel consistent. I also kept a dark theme with spacing and contrast tuned for readability. The intent was to make the interface look clean while still being simple to maintain.

A challenge during development was balancing interactivity with readability. It is easy to add too much JavaScript and make a student project hard to explain. I kept interactions small and clear: simple sort buttons, search filter, top filter buttons, and lightweight chart controls. Another challenge was keeping chart colors readable on a dark background. I solved this by using a shared color palette and subtle styling.

This project was developed with assistance from AI tools like ChatGPT and GitHub Copilot for guidance and polish. I reviewed, Implemented and understood all final logic and structure.

Overall, this project demonstrates a complete Flask workflow: database-driven pages, match tracking, ranking display, and a dashboard that is useful in real club scenarios. It is designed to be practical, easy to present, and easy to explain in a live demo.

## How to Run

### Prerequisites

- Python 3.13 (or later)
- pip (included with Python)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and python-dotenv. All other packages are pulled in automatically.

### 2. Set up the database

The app expects a SQLite database file. By default it looks for `../ChessAdmin.sqlite3` (one folder above the project). You can override this with an environment variable:

```bash
# Linux / macOS
export CHESS_DB_PATH="/path/to/ChessAdmin.sqlite3"

# Windows PowerShell
$env:CHESS_DB_PATH = "C:\path\to\ChessAdmin.sqlite3"
```

A pre-populated database is included in the repository root so the app works out of the box.

### 3. Start the app

```bash
python app.py
```

Then open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

### 4. Run the tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 10 tests should pass. They cover members, match recording, history, profile, and ranking.

### Environment variables (optional)

| Variable | Purpose | Default |
| --- | --- | --- |
| `CHESS_DB_PATH` | Path to the SQLite database file | `../ChessAdmin.sqlite3` |
| `CHESS_SECRET_KEY` | Flask session secret key | Dev fallback value |
| `CHESS_AUTH_PHASE_ENABLED` | Enable login/register routes (`true`/`false`) | `false` |
