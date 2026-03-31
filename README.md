```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    CHESS CLUB WEB APPLICATION                                  ║
║                    TECHNICAL USER MANUAL v1.0                                  ║
║                    Author: [Your Name]                                         ║
║                    Project: ChessWBA                                           ║
╚══════════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABLE OF CONTENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Project Overview
  2. Tech Stack Breakdown
  3. Project Structure Explained
  4. Database Design
  5. How The Ranking System Works
  6. Every Feature Explained
  7. Step-By-Step Setup Guide
  8. How To Run The Application
  9. Every Route Explained
  10. Troubleshooting Guide
  11. Security Measures
  12. Future Improvements


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — PROJECT OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Chess Club Web Application (ChessWBA) is a full-stack web application
built to manage the members, rankings, and match history of a local chess
club. I designed and built this application from scratch using Python, Flask,
SQLite, HTML, CSS, and JavaScript.

The core idea is simple: every member of the club has a rank. When two
members play a match, their ranks update automatically based on who won,
who lost, or whether it was a draw. The app handles all of that logic
behind the scenes so the club never has to calculate rankings manually.

The application is inspired by the CS50 Finance project structure — meaning
it follows the same pattern of a Python Flask backend serving Jinja2 HTML
templates, with a SQLite database storing all data. Anyone familiar with
CS50 Finance will immediately understand how this project is organized.

What the app does:
  - Lets members register and log in securely
  - Displays a live leaderboard ranked from best to worst player
  - Shows every member's public profile with their stats
  - Lets members upload a profile picture
  - Records match results between any two players
  - Automatically recalculates and updates rankings after every match
  - Keeps a full history of every match ever played


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — TECH STACK BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Here is every technology I used and exactly why I chose it:

PYTHON (Backend Language)
  Python is the server-side language that powers the entire application.
  It handles all incoming requests, processes form data, talks to the
  database, runs the ranking logic, and sends back the correct HTML page.
  I chose Python because it is clean, readable, and pairs perfectly
  with Flask.

FLASK (Web Framework)
  Flask is a lightweight Python web framework. It is what turns my Python
  code into a web server that can receive HTTP requests from a browser.
  Every URL in the app (like /login or /match) is defined as a Flask
  route in app.py. Flask also handles sessions, flash messages, and
  file uploads.

SQLITE (Database)
  SQLite is a file-based relational database. All data — users, matches,
  passwords — is stored in a single file called chess.db. I chose SQLite
  because it requires zero configuration, runs without a separate database
  server, and is perfect for a project of this size. The cs50 SQL library
  is used to query it safely.

CS50 SQL LIBRARY
  This is the same database library used in CS50 Finance. It wraps SQLite
  and makes queries safe by automatically using parameterized placeholders,
  which prevents SQL injection attacks. Every database call in app.py uses:
    db.execute("SELECT * FROM users WHERE id = ?", user_id)

JINJA2 (HTML Templating)
  Jinja2 is Flask's built-in templating engine. It lets me write HTML files
  that contain dynamic Python-like expressions. For example:
    {% for member in members %}
      <tr>{{ member.first_name }}</tr>
    {% endfor %}
  All templates extend layout.html, which means the sidebar and navigation
  are only written once and shared across every page.

HTML & CSS (Frontend)
  All pages are written in standard HTML5. The styles.css file contains
  every visual rule — colors, fonts, layouts, buttons, tables, badges,
  and responsive mobile styles. I used CSS variables so the color scheme
  can be changed in one place.

JAVASCRIPT (Frontend Interactivity)
  Vanilla JavaScript is used for three things:
    1. Real-time search filtering on the leaderboard and members pages
    2. Live rank change preview on the match recording page
       (fetches /api/preview_match without reloading the page)
    3. Instant avatar preview when a user selects a new photo

WERKZEUG (Security + File Uploads)
  Werkzeug is a library that Flask is built on. I use two things from it:
    - generate_password_hash() to hash passwords before storing them
    - check_password_hash() to verify passwords at login
    - secure_filename() to safely handle uploaded file names

FLASK-SESSION (Server-Side Sessions)
  Flask-Session stores session data on the server rather than in a browser
  cookie. This is more secure because the actual user data never leaves
  the server. The browser only holds a session ID.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — PROJECT STRUCTURE EXPLAINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

chess-club/
│
├── app.py                  ← THE BRAIN. Every route, every page,
│                             every form submission is handled here.
│                             This is the file you run to start the app.
│
├── helpers.py              ← HELPER FUNCTIONS. Contains:
│                             - login_required decorator
│                             - apply_ranking_rules()
│                             - preview_ranking_rules()
│                             - resequence_ranks()
│                             - allowed_file()
│                             - get_initials()
│
├── schema.sql              ← DATABASE BLUEPRINT. The SQL commands that
│                             create the users and matches tables.
│                             Runs automatically on first startup.
│
├── chess.db                ← THE DATABASE FILE. Created automatically
│                             when the app runs for the first time.
│                             All members and match data lives here.
│
├── requirements.txt        ← LIST OF DEPENDENCIES. Every Python package
│                             the app needs. Run:
│                             pip install -r requirements.txt
│
├── static/
│   ├── styles.css          ← ALL VISUAL STYLING. Every color, font,
│   │                         layout, button, table, badge, and
│   │                         responsive rule is defined here.
│   │
│   └── uploads/            ← PROFILE PICTURES FOLDER. When a user
│       └── .gitkeep          uploads a photo, it is saved here.
│                             The filename is stored in the database.
│
└── templates/
    ├── layout.html         ← BASE TEMPLATE. Contains the sidebar,
    │                         navigation, flash messages. Every other
    │                         template extends this file.
    │
    ├── index.html          ← LEADERBOARD. The home page. Shows all
    │                         members ranked 1 to n with stat cards.
    │
    ├── login.html          ← LOGIN PAGE. Username and password form.
    │
    ├── register.html       ← REGISTRATION PAGE. New member signup form.
    │
    ├── profile.html        ← PUBLIC PROFILE. Shows any member's stats,
    │                         avatar, win/draw/loss record, recent matches.
    │
    ├── edit_profile.html   ← EDIT OWN PROFILE. Update personal info
    │                         and upload a profile picture.
    │
    ├── members.html        ← ALL MEMBERS TABLE. Searchable list of
    │                         every club member.
    │
    ├── match.html          ← RECORD A MATCH. Select two players,
    │                         pick a result, see live rank preview,
    │                         confirm to update rankings.
    │
    ├── history.html        ← MATCH HISTORY. Every match ever recorded
    │                         with rank change indicators.
    │
    ├── apology.html        ← ERROR PAGE. Shown when something goes
    │                         wrong, with a friendly message.
    │
    ├── 404.html            ← NOT FOUND PAGE. Shown when a URL
    │                         does not exist.
    │
    └── 500.html            ← SERVER ERROR PAGE. Shown when an
                              unexpected server error occurs.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — DATABASE DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The database has two tables: users and matches.

TABLE: users
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ Column          │ What it stores                                           │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ id              │ Unique auto-incrementing number for each user            │
│ username        │ Unique login name chosen at registration                 │
│ hash            │ Bcrypt-hashed password (never stored as plain text)      │
│ email           │ Unique email address                                     │
│ first_name      │ Member's first name                                      │
│ last_name       │ Member's last name                                       │
│ birthday        │ Date of birth (YYYY-MM-DD format)                        │
│ games_played    │ Total number of club matches played (increments after    │
│                 │ each recorded match)                                     │
│ rank            │ Current club ranking (1 = best, n = last)               │
│ avatar_filename │ The saved filename of the uploaded profile picture.      │
│                 │ NULL if no photo uploaded yet                            │
│ last_login      │ Timestamp of the most recent login                      │
│ created_at      │ Timestamp of when the account was created               │
└─────────────────┴──────────────────────────────────────────────────────────┘

TABLE: matches
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ Column          │ What it stores                                           │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ id              │ Unique auto-incrementing match ID                        │
│ player1_id      │ Foreign key → users.id for player 1                     │
│ player2_id      │ Foreign key → users.id for player 2                     │
│ winner_id       │ Foreign key → users.id of winner. NULL means draw       │
│ p1_rank_before  │ Player 1's rank before this match was played            │
│ p2_rank_before  │ Player 2's rank before this match was played            │
│ p1_rank_after   │ Player 1's rank after ranking rules applied             │
│ p2_rank_after   │ Player 2's rank after ranking rules applied             │
│ played_at       │ Timestamp of when the match was recorded                │
└─────────────────┴──────────────────────────────────────────────────────────┘

WHY I STORE RANKS BEFORE AND AFTER:
  I store the rank snapshot at the time of each match so the history
  page can show exactly how much each player moved after every game.
  This means even if ranks change later, the historical record is
  always accurate.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — HOW THE RANKING SYSTEM WORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank 1 is the BEST player. Rank n is the last player. A lower number
always means a better position.

RULE 1 — HIGHER-RANKED PLAYER WINS:
  No change for either player.
  Example: Rank 3 beats Rank 8 → both stay the same.
  Reason: The better player is expected to win. No reward needed.

RULE 2 — DRAW:
  The lower-ranked player moves up 1 position ONLY if the gap
  between their ranks is greater than 1.
  Example A: Rank 10 draws with Rank 15 → Rank 15 becomes Rank 14.
  Example B: Rank 10 draws with Rank 11 → no change (gap is only 1).
  Reason: A draw against a much better player is a strong result
  and deserves a small reward. Adjacent players drawing is normal.

RULE 3 — LOWER-RANKED PLAYER WINS (UPSET):
  - Higher-ranked player drops 1 position
  - Lower-ranked player moves up by: floor(difference / 2)
  Example: Rank 10 vs Rank 16. Rank 16 wins.
    difference = 16 - 10 = 6
    Rank 10 becomes Rank 11 (drops 1)
    Rank 16 moves up by floor(6/2) = 3 → becomes Rank 13
  Reason: Beating a much better player is a significant achievement
  and deserves a meaningful jump up the rankings.

RESEQUENCING:
  After every match, I call resequence_ranks() which re-numbers
  all players from 1 to n in order. This prevents any gaps or
  duplicate rank numbers from appearing in the table.

WHERE THIS LOGIC LIVES:
  All ranking logic is in helpers.py in two functions:
    - apply_ranking_rules() → mutates and saves real ranks
    - preview_ranking_rules() → calculates without saving,
      used for the live preview on the match page


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — EVERY FEATURE EXPLAINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGISTER:
  A new member fills in their username, email, first name, last name,
  birthday, password, and password confirmation. The backend validates
  every field — checking the username is not already taken, the email
  is unique, the passwords match, and the password is at least 6
  characters. The password is hashed with werkzeug before being saved.
  The new member is assigned a rank equal to the current total number
  of members + 1, meaning they start at the bottom of the leaderboard.

LOGIN:
  The member enters their username and password. Flask checks the
  username exists in the database, then uses check_password_hash to
  verify the password against the stored hash. If correct, the user's
  id is stored in the Flask session, their last_login timestamp is
  updated, and they are redirected to the leaderboard.

LOGOUT:
  Calling session.clear() wipes all session data from the server.
  The user is redirected to the login page.

LEADERBOARD (HOME PAGE):
  Fetches all members from the database ordered by rank ascending.
  Displays them in a table with gold, silver, and bronze badges for
  the top 3. Stat cards at the top show total members, total matches
  played, the current top player, and the logged-in user's own rank.
  A "You" badge highlights the current user's row. The search box
  uses JavaScript to filter rows in real time without any page reload.

MEMBERS PAGE:
  Same as leaderboard but without the stat cards. Shows every member
  in a searchable table. Each row links to that member's profile.

PROFILE PAGE:
  Shows a public profile for any member. Displays their avatar (or
  an initials circle if no photo uploaded), full name, email, rank
  badge, games played, and win/draw/loss statistics. A win rate bar
  visualizes their performance. Their 10 most recent matches are
  listed at the bottom. If the logged-in user is viewing their own
  profile, an Edit Profile button appears.

EDIT PROFILE:
  Lets a member update their first name, last name, email, and
  birthday. They can also upload a profile picture. When a file is
  selected, JavaScript immediately shows a preview of the image
  before it is uploaded. On submission, the file is validated
  (must be jpg, jpeg, png, or gif, under 2MB), saved to
  static/uploads/ with a secure filename, and the filename is
  stored in the database.

RECORD MATCH:
  Two dropdowns list all members sorted by rank. The user selects
  Player 1 and Player 2, then clicks one of three result buttons:
  Player 1 Wins, Draw, or Player 2 Wins. As soon as both players
  and a result are selected, JavaScript sends a fetch request to
  /api/preview_match and displays a live preview showing each
  player's current rank and what their new rank will be. The user
  can then confirm to officially record the match and update all
  rankings in the database.

MATCH HISTORY:
  Shows every recorded match in reverse chronological order. Each
  row shows the date, both player names (linking to their profiles),
  the result, and rank change pills (green arrow up or red arrow
  down) showing how much each player moved.

LIVE RANK PREVIEW:
  This is one of the most important features. When recording a
  match, the user does not have to guess what will happen to the
  rankings. The JavaScript on match.html calls the /api/preview_match
  endpoint which runs the ranking logic without saving anything and
  returns JSON. The JavaScript then updates the preview box on the
  page showing the exact rank change before the user confirms.

PROFILE PICTURE UPLOAD:
  When editing a profile, the user selects an image file. JavaScript
  reads the file with FileReader and displays an instant preview.
  When the form is submitted, Flask saves the file to static/uploads/
  using secure_filename to sanitize the filename, and stores the
  filename in the users table. The profile page then loads the image
  from static/uploads/filename.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — STEP-BY-STEP SETUP GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT YOU NEED INSTALLED FIRST:
  - Python 3.10 or higher   → https://python.org
  - pip (comes with Python)
  - VS Code                 → https://code.visualstudio.com
  - VS Code Python extension (Microsoft)

STEP 1 — OPEN THE PROJECT IN VS CODE:
  1. Open VS Code
  2. Click File → Open Folder
  3. Select the ChessWBA folder
  4. You should see app.py, helpers.py, etc. in the file explorer

STEP 2 — OPEN A TERMINAL IN VS CODE:
  Press Ctrl + ` (backtick) or go to Terminal → New Terminal
  You should see a terminal at the bottom of VS Code

STEP 3 — NAVIGATE TO THE PROJECT FOLDER:
  If you are not already in the ChessWBA folder, type:

    cd path/to/ChessWBA

  Example on Windows:
    cd E:\NetStock\ChessWBA

  Example on Mac/Linux:
    cd ~/projects/ChessWBA

STEP 4 — INSTALL ALL DEPENDENCIES:
  Run this single command. It installs every package the app needs:

    pip install -r requirements.txt

  This installs: Flask, Flask-Session, werkzeug, cs50
  Wait for it to finish. You will see "Successfully installed..." messages.

STEP 5 — VERIFY THE FOLDER STRUCTURE:
  Make sure static/uploads/ folder exists. If it does not, create it:

    Windows:
      mkdir static\uploads

    Mac/Linux:
      mkdir -p static/uploads

STEP 6 — THE DATABASE:
  You do NOT need to run schema.sql manually. The app.py file is written
  to automatically run schema.sql and create chess.db the first time
  the app starts. You will see chess.db appear in your project folder
  after the first run.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — HOW TO RUN THE APPLICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STARTING THE APP:
  In your VS Code terminal, make sure you are in the ChessWBA folder,
  then run:

    python app.py

  You will see output like this:
    * Running on http://127.0.0.1:5000
    * Debug mode: on
    * Restarting with stat

OPENING IN THE BROWSER:
  Open your browser (Chrome or Edge recommended) and go to:

    http://localhost:5000

  You will be redirected to the login page automatically because
  no one is logged in yet.

FIRST TIME USING THE APP:
  1. Click "Register" to create the first account
  2. Fill in all fields and submit
  3. You will be redirected to login
  4. Log in with your new username and password
  5. You will land on the leaderboard as the only member (Rank 1)
  6. Register more members to populate the rankings

STOPPING THE APP:
  Go back to the VS Code terminal and press:
    Ctrl + C
  This stops the Flask server.

RESTARTING THE APP:
  Just run python app.py again. Your data is safe in chess.db.

RUNNING IN PRODUCTION MODE (optional, advanced):
  The default debug=True mode is fine for development.
  To run without debug mode, change the last line of app.py to:
    app.run(debug=False)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 9 — EVERY ROUTE EXPLAINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET  /                  Home page. Shows leaderboard. Requires login.
GET  /login             Shows the login form.
POST /login             Processes login form submission.
GET  /register          Shows the registration form.
POST /register          Processes registration form submission.
GET  /logout            Logs out the current user and redirects to login.
GET  /members           Shows all members in a searchable table.
GET  /profile/<id>      Shows the public profile of the member with that id.
GET  /edit_profile      Shows the edit profile form for the logged-in user.
POST /edit_profile      Saves updated profile info and/or new avatar photo.
GET  /match             Shows the match recording form.
POST /match             Processes the match result and updates all rankings.
GET  /history           Shows all recorded matches in reverse order.
POST /api/preview_match JSON endpoint. Returns rank change preview without
                        saving anything. Used by JavaScript on match page.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 10 — TROUBLESHOOTING GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: "ModuleNotFoundError: No module named 'flask'"
SOLUTION:
  You have not installed the dependencies yet. Run:
    pip install -r requirements.txt

PROBLEM: "ModuleNotFoundError: No module named 'cs50'"
SOLUTION:
  The cs50 library needs to be installed separately sometimes:
    pip install cs50

PROBLEM: The browser shows "This site can't be reached"
SOLUTION:
  The Flask server is not running. Go back to VS Code terminal and run:
    python app.py
  Then refresh the browser.

PROBLEM: "Address already in use" error in terminal
SOLUTION:
  Port 5000 is already being used by another process. Either stop
  that process, or change the port in the last line of app.py:
    app.run(debug=True, port=5001)
  Then visit http://localhost:5001

PROBLEM: Profile pictures are not showing up
SOLUTION:
  Make sure the static/uploads/ folder exists:
    mkdir static\uploads   (Windows)
    mkdir -p static/uploads  (Mac/Linux)

PROBLEM: "OperationalError: no such table: users"
SOLUTION:
  The database has not been created yet, or schema.sql failed.
  Delete chess.db if it exists and restart the app:
    del chess.db   (Windows)
    rm chess.db    (Mac/Linux)
  Then run python app.py again.

PROBLEM: Changes to CSS or HTML are not showing in the browser
SOLUTION:
  Your browser is caching the old files. Do a hard refresh:
    Windows/Linux: Ctrl + Shift + R
    Mac: Cmd + Shift + R

PROBLEM: The rank preview is not showing on the match page
SOLUTION:
  Open browser developer tools (F12), go to the Console tab and
  look for JavaScript errors. Also check the Network tab to see
  if the /api/preview_match request is succeeding.

PROBLEM: "werkzeug.exceptions.RequestEntityTooLarge"
SOLUTION:
  The uploaded file is larger than 2MB. Use a smaller image.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 11 — SECURITY MEASURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every security decision I made and why:

PASSWORDS ARE NEVER STORED AS PLAIN TEXT:
  Every password is hashed using werkzeug's generate_password_hash
  before being saved to the database. Even if someone accessed
  chess.db directly, they would only see hashed strings, not
  actual passwords.

PARAMETERIZED SQL QUERIES:
  Every database query uses ? placeholders:
    db.execute("SELECT * FROM users WHERE username = ?", username)
  This completely prevents SQL injection attacks. User input is
  never concatenated directly into SQL strings.

LOGIN REQUIRED ON ALL PRIVATE ROUTES:
  The @login_required decorator in helpers.py is applied to every
  route except /login and /register. If an unauthenticated user
  tries to access any page directly, they are immediately
  redirected to /login.

USERS CAN ONLY EDIT THEIR OWN PROFILE:
  The /edit_profile route checks that the logged-in user's session
  id matches the profile being edited. No one can modify another
  member's information.

SECURE FILE UPLOADS:
  - secure_filename() from werkzeug sanitizes uploaded filenames,
    removing any path traversal characters or dangerous names
  - Only jpg, jpeg, png, and gif extensions are accepted
  - File size is capped at 2MB via MAX_CONTENT_LENGTH
  - Files are saved to static/uploads/ which is separate from
    application code

SERVER-SIDE SESSIONS:
  Flask-Session stores session data on the server. The browser
  only holds a session ID cookie, not the actual user data.
  This prevents session tampering.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 12 — FUTURE IMPROVEMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These are features I would add in the next version:

  1. ADMIN PANEL
     A separate admin role that can add, edit, and delete members,
     override rankings, and delete incorrect match records.

  2. ELO RATING SYSTEM
     Replace the simple rank movement system with a proper ELO
     rating system for more accurate skill representation.

  3. TOURNAMENTS
     A tournament bracket system where members can be entered into
     a structured competition with automated bracket progression.

  4. EMAIL NOTIFICATIONS
     Send an email to both players when a match is recorded against
     them, showing the result and their new rank.

  5. MATCH CHALLENGES
     Members can challenge other members to a match through the app,
     and the challenged member can accept or decline.

  6. RANK HISTORY GRAPH
     A line graph on each member's profile showing how their rank
     has changed over time across all matches.

  7. PASSWORD RESET
     A forgot password flow using email verification so members can
     reset their password without admin intervention.

  8. POSTGRESQL MIGRATION
     For a larger club, migrate from SQLite to PostgreSQL for better
     performance with concurrent users.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK REFERENCE — ALL COMMANDS YOU NEED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  INSTALL DEPENDENCIES:
    pip install -r requirements.txt

  CREATE UPLOADS FOLDER (if missing):
    Windows:   mkdir static\uploads
    Mac/Linux: mkdir -p static/uploads

  START THE APP:
    python app.py

  OPEN IN BROWSER:
    http://localhost:5000

  STOP THE APP:
    Ctrl + C in the terminal

  RESET THE DATABASE (WARNING: deletes all data):
    Windows:   del chess.db
    Mac/Linux: rm chess.db
    Then run:  python app.py

  HARD REFRESH BROWSER (clear cache):
    Windows/Linux: Ctrl + Shift + R
    Mac:           Cmd + Shift + R

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF MANUAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
