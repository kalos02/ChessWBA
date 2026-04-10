# -*- coding: utf-8 -*-
# This project was developed with assistance from AI tools (ChatGPT and GitHub Copilot) for guidance and optimization. All logic and understanding were implemented and reviewed by the author.
# Recommended: Python 3.x and install requirements.txt
# Always activate the venv before running: .\venv\Scripts\activate
"""
ChessWBA Flask app (backend)

Purpose:
- Provides user auth (register/login/logout) FOR Phase 2 only
- Manages users, matches, rankings, and profiles
- Exposes API endpoint `/api/preview_match` for frontend live preview
- Renders templates from `templates/`

Database contract used by this file:
- auth_user
- ChessAdminApp_player
- ChessAdminApp_match
"""

import os
import re
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import (
    login_required,
    get_initials,
)


# -----------------------------------------------------------------------------
# Database Access Layer
# -----------------------------------------------------------------------------
class Database:
    """Simple SQLite wrapper that returns SELECT rows as dictionaries."""

    def __init__(self, db_path):
        self.db_path = db_path

    def execute(self, query, *args):
        """Execute SQL and return list[dict] for SELECT/PRAGMA queries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, args)
            if query.strip().upper().startswith(("SELECT", "PRAGMA", "WITH")):
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
            conn.commit()
            conn.close()
            return None
        except Exception as exc:
            conn.close()
            raise exc


app = Flask(__name__)

# -----------------------------------------------------------------------------
# App Configuration
# -----------------------------------------------------------------------------
# App/session configuration.
app.config["SECRET_KEY"] = os.getenv("CHESS_SECRET_KEY", "chess-club-secret-key-2024")
app.config["SESSION_PERMANENT"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["AUTH_PHASE_ENABLED"] = os.getenv("CHESS_AUTH_PHASE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
app.config["DB_PATH"] = os.getenv("CHESS_DB_PATH", r"E:\Skaak\ChessAdmin.sqlite3")

# Database connection.
db = Database(app.config["DB_PATH"])


REQUIRED_DB_SCHEMA = {
    "auth_user": {
        "id",
        "username",
        "password",
        "email",
        "first_name",
        "last_name",
        "last_login",
        "date_joined",
    },
    "ChessAdminApp_player": {
        "id",
        "first_name",
        "last_name",
        "ranking",
        "points",
        "date_of_birth",
    },
    "ChessAdminApp_match": {
        "id",
        "scheduled_date",
        "match_result",
        "player_one_entry_ranking",
        "player_two_entry_ranking",
        "player_one_ranking_change",
        "player_two_ranking_change",
        "player_one_id",
        "player_two_id",
        "winner_id",
    },
}


def validate_required_schema():
    """Fail fast if required tables/columns for Phase 1 are missing."""
    table_rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'") or []
    existing_tables = {row["name"] for row in table_rows}
    missing_items = []

    for table_name, required_columns in REQUIRED_DB_SCHEMA.items():
        if table_name not in existing_tables:
            missing_items.append("missing table '{}'".format(table_name))
            continue

        column_rows = db.execute("PRAGMA table_info({})".format(table_name)) or []
        existing_columns = {row["name"] for row in column_rows}
        missing_columns = sorted(required_columns - existing_columns)

        if missing_columns:
            missing_items.append(
                "missing columns in '{}': {}".format(table_name, ", ".join(missing_columns))
            )

    if missing_items:
        raise RuntimeError("Database schema validation failed: {}".format("; ".join(missing_items)))


validate_required_schema()

# Ensure upload folder exists once at startup instead of checking each request.
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# -----------------------------------------------------------------------------
# Shared Template Context + Utility Helpers
# -----------------------------------------------------------------------------
@app.context_processor
def inject_helpers():
    """Make helper function and current user available in all templates."""
    current_user = None

    if session.get("user_id"):
        user_rows = db.execute(
            """
            SELECT
                au.id,
                au.username,
                au.email,
                au.first_name,
                au.last_name,
                au.last_login,
                cp.ranking AS rank,
                cp.points,
                cp.date_of_birth,
                cp.id AS player_id
            FROM auth_user au
            LEFT JOIN ChessAdminApp_player cp ON cp.id = au.id
            WHERE au.id = ?
            """,
            session["user_id"],
        )
        current_user = user_rows[0] if user_rows else None

    return {
        "get_initials": get_initials,
        "current_user": current_user,
    }


def apology(message, code=400):
    """Render apology template with status code."""
    return render_template("apology.html", message=message), code


def validate_email(email):
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def normalize_datetime(value):
    """Return a datetime object for template-safe strftime usage, else None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    # Try common SQLite/auth timestamp formats first.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    # Fallback for ISO-like strings (including T separator).
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_player_form_data(form_data):
    """Read members form fields from request.form (Add/Edit modal form)."""
    return {
        "first_name": form_data.get("first_name", "").strip(),
        "last_name": form_data.get("last_name", "").strip(),
        "city": form_data.get("city", "").strip() or None,
        "ranking_raw": form_data.get("ranking", "").strip(),
        "points_raw": form_data.get("points", "").strip(),
        "date_of_birth": form_data.get("date_of_birth", "").strip() or None,
    }


def get_player_id_raw(form_data):
    """Read raw playerId string from members form hidden input name='id'."""
    return form_data.get("id", "").strip()


def is_empty(*values):
    """Return True when any required value is empty."""
    return any(not value for value in values)


def parse_ranking_and_points(ranking_raw, points_raw):
    """Convert ranking and points form fields to integers."""
    return int(ranking_raw), int(points_raw)


def parse_player_id(player_id_raw):
    """Convert playerId field to integer; id is the unique record identifier."""
    return int(player_id_raw)


def get_player_count():
    """Return total number of players currently stored."""
    count_rows = db.execute("SELECT COUNT(*) AS count FROM ChessAdminApp_player")
    return int(count_rows[0]["count"]) if count_rows else 0


def clamp_rank_for_add(requested_rank):
    """For add flow, valid rank window is 1..(current_count + 1)."""
    current_count = get_player_count()
    return max(1, min(int(requested_rank), current_count + 1))


def clamp_rank_for_edit(requested_rank):
    """For edit flow, valid rank window is 1..current_count."""
    current_count = get_player_count()
    if current_count <= 0:
        return 1
    return max(1, min(int(requested_rank), current_count))


def has_rank_conflict(rank, points, exclude_player_id=None):
    """
    Return True when target rank is occupied by a player with different points.

    Shared rank is only valid when points are equal.
    """
    if exclude_player_id is None:
        rows = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM ChessAdminApp_player
            WHERE ranking = ?
              AND points != ?
            """,
            rank,
            points,
        )
    else:
        rows = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM ChessAdminApp_player
            WHERE id != ?
              AND ranking = ?
              AND points != ?
            """,
            exclude_player_id,
            rank,
            points,
        )

    return bool(rows and int(rows[0]["count"]) > 0)


def shift_ranks_for_add(new_rank, new_points):
    """
    Add flow rank adjustment.

    If target rank is occupied by a player with different points, the slot is opened
    by shifting all players at/after that rank down.

    If target rank players have the same points, rank sharing is allowed (no shift).

    Returns the safe, clamped rank that should be assigned to the new player.
    """
    safe_rank = clamp_rank_for_add(new_rank)

    if has_rank_conflict(safe_rank, new_points):
        db.execute(
            """
            UPDATE ChessAdminApp_player
            SET ranking = ranking + 1
            WHERE ranking >= ?
            """,
            safe_rank,
        )

    return safe_rank


def shift_ranks_for_edit(player_id, new_rank, new_points):
    """
    Edit flow rank adjustment.

    If target rank has a different-points occupant, open that slot by shifting
    all other players at/after target rank down.

    Shared rank is allowed only when points are equal.

    Returns the safe, clamped rank that should be written to the edited player row.
    """
    current_rank_rows = db.execute(
        "SELECT ranking FROM ChessAdminApp_player WHERE id = ?",
        player_id,
    )
    if not current_rank_rows:
        # Keep route behavior stable if the id does not exist.
        return clamp_rank_for_edit(new_rank)

    safe_rank = clamp_rank_for_edit(new_rank)

    if has_rank_conflict(safe_rank, new_points, exclude_player_id=player_id):
        # Keep edited player at requested rank and displace current different-points occupants.
        db.execute(
            """
            UPDATE ChessAdminApp_player
            SET ranking = ranking + 1
            WHERE id != ?
              AND ranking >= ?
            """,
            player_id,
            safe_rank,
        )

    return safe_rank


def normalize_rankings_with_ties():
    """
    Compact rankings to a clean ascending sequence while preserving valid ties.

    Rules enforced:
    - No gaps in rank numbers.
    - Players can share a rank only when they also share the same points.
    """
    players = db.execute(
        """
        SELECT id, ranking, points
        FROM ChessAdminApp_player
        ORDER BY ranking ASC, id ASC
        """
    ) or []

    if not players:
        return

    assigned_rank = 1
    prev_original_rank = players[0]["ranking"]
    prev_points = players[0]["points"]

    updates = []
    if players[0]["ranking"] != assigned_rank:
        updates.append((assigned_rank, players[0]["id"]))

    for player in players[1:]:
        original_rank = player["ranking"]
        points = player["points"]

        if original_rank == prev_original_rank and points == prev_points:
            # Valid tie: same original rank and same points.
            next_rank = assigned_rank
        else:
            next_rank = assigned_rank + 1

        if original_rank != next_rank:
            updates.append((next_rank, player["id"]))

        assigned_rank = next_rank
        prev_original_rank = original_rank
        prev_points = points

    if not updates:
        return

    # Use one transaction for all ranking rewrites to keep edit/add/delete fast.
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE ChessAdminApp_player SET ranking = ? WHERE id = ?",
            updates,
        )
        conn.commit()


@app.before_request
def before_request():
    """Lightweight request debug logging."""
    print("BACKEND DEBUG: Received request to {} with method {}".format(request.path, request.method))


# -----------------------------------------------------------------------------
# Authentication Routes
# -----------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new auth_user and matching ChessAdminApp_player row."""
    if not app.config.get("AUTH_PHASE_ENABLED", False):
        return apology("Authentication is disabled for this phase.", 503)

    print("BACKEND DEBUG: Received request to /register with body:", request.form.to_dict())
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirmation", "")

    if not username:
        flash("Username is required.", "error")
        return render_template("register.html")

    if not email or not validate_email(email):
        flash("Valid email is required.", "error")
        return render_template("register.html")

    if not first_name:
        flash("First name is required.", "error")
        return render_template("register.html")

    if not last_name:
        flash("Last name is required.", "error")
        return render_template("register.html")

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return render_template("register.html")

    if password != confirmation:
        flash("Passwords do not match.", "error")
        return render_template("register.html")

    if db.execute("SELECT id FROM auth_user WHERE username = ?", username):
        flash("Username already exists.", "error")
        return render_template("register.html")

    if db.execute("SELECT id FROM auth_user WHERE email = ?", email):
        flash("Email already exists.", "error")
        return render_template("register.html")

    try:
        password_hash = generate_password_hash(password)
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN")
            cursor.execute("SELECT COALESCE(MAX(id), 0) FROM auth_user")
            max_auth_id = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(MAX(id), 0) FROM ChessAdminApp_player")
            max_player_id = cursor.fetchone()[0]
            user_id = max(max_auth_id, max_player_id) + 1

            cursor.execute(
                """
                INSERT INTO auth_user
                    (id, username, password, email, first_name, last_name,
                     is_active, is_staff, is_superuser, last_login, date_joined)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, NULL, datetime('now'))
                """,
                (user_id, username, password_hash, email, first_name, last_name),
            )

            cursor.execute("SELECT COUNT(*) FROM ChessAdminApp_player")
            initial_rank = cursor.fetchone()[0] + 1

            cursor.execute(
                """
                INSERT INTO ChessAdminApp_player
                    (id, first_name, last_name, date_joined, date_of_birth,
                     country, city, is_active, ranking, points)
                VALUES (?, ?, ?, datetime('now'), NULL, NULL, NULL, 1, ?, 0)
                """,
                (user_id, first_name, last_name, initial_rank),
            )
            conn.commit()

        flash("Registered successfully! Please log in.", "success")
        return redirect("/login")
    except Exception as exc:
        print("Registration error: {}".format(exc))
        flash("An error occurred during registration.", "error")
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user against auth_user and start session."""
    if not app.config.get("AUTH_PHASE_ENABLED", False):
        return apology("Authentication is disabled for this phase.", 503)

    print("BACKEND DEBUG: Received request to /login with body:", request.form.to_dict())
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username:
        flash("Username is required.", "error")
        return render_template("login.html")

    if not password:
        flash("Password is required.", "error")
        return render_template("login.html")

    users = db.execute("SELECT * FROM auth_user WHERE username = ?", username)
    if not users:
        flash("Invalid username or password.", "error")
        return render_template("login.html")

    user = users[0]
    if not check_password_hash(user["password"], password):
        flash("Invalid username or password.", "error")
        return render_template("login.html")

    db.execute("UPDATE auth_user SET last_login = ? WHERE id = ?", datetime.now().isoformat(), user["id"])

    session["user_id"] = user["id"]
    session["player_id"] = user["id"]
    flash("Welcome back, {}!".format(user["first_name"]), "success")
    return redirect("/")


@app.route("/logout")
def logout():
    """Log out the current user."""
    if not app.config.get("AUTH_PHASE_ENABLED", False):
        return redirect("/")

    print("BACKEND DEBUG: Received request to /logout with params:", request.args.to_dict())
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/login")


# -----------------------------------------------------------------------------
# Application Routes
# -----------------------------------------------------------------------------
@app.route("/")

def index():
    """Leaderboard home page."""
    print("BACKEND DEBUG: Received request to / with user_id:", session.get("user_id"))
    current_user_idPy = session.get("user_id")

    # Leaderboard users with match stats.
    usersPy = db.execute(
        """
        WITH match_stats AS (
            SELECT
                player_id,
                COUNT(*) AS matches_played,
                SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) AS wins
            FROM (
                SELECT m.player_one_id AS player_id,
                       CASE WHEN m.winner_id = m.player_one_id THEN 1 ELSE 0 END AS won
                FROM ChessAdminApp_match m
                UNION ALL
                SELECT m.player_two_id AS player_id,
                       CASE WHEN m.winner_id = m.player_two_id THEN 1 ELSE 0 END AS won
                FROM ChessAdminApp_match m
            ) x
            GROUP BY player_id
        )
        SELECT
            cp.id,
            cp.first_name,
            cp.last_name,
            cp.ranking AS rank,
            cp.points,
            cp.date_of_birth,
            au.email,
            au.username,
            au.last_login,
            COALESCE(ms.matches_played, 0) AS matches_played,
            CASE
                WHEN COALESCE(ms.matches_played, 0) = 0 THEN 0
                ELSE ROUND((COALESCE(ms.wins, 0) * 100.0) / ms.matches_played, 1)
            END AS win_ratio
        FROM ChessAdminApp_player cp
        LEFT JOIN auth_user au ON cp.id = au.id
        LEFT JOIN match_stats ms ON ms.player_id = cp.id
        ORDER BY cp.ranking ASC
        """
    ) or []

    points_usersPy = sorted(usersPy, key=lambda u: (u["points"], -u["rank"]), reverse=True)

    total_membersPy = len(usersPy) if usersPy else 0
    match_count_rows = db.execute("SELECT COUNT(*) AS count FROM ChessAdminApp_match")
    total_matchesPy = match_count_rows[0]["count"] if match_count_rows else 0
    top_playerPy = usersPy[0] if usersPy else None

    user_rankPy = 0
    if current_user_idPy is not None:
        current_user_rows = db.execute(
            "SELECT ranking FROM ChessAdminApp_player WHERE id = ?",
            current_user_idPy,
        )
        user_rankPy = current_user_rows[0]["ranking"] if current_user_rows else 0

    # Club-wide outcomes: each match is decisive (one winner) or draw.
    outcome_rows = db.execute(
        """
        SELECT
            SUM(CASE WHEN winner_id IS NOT NULL THEN 1 ELSE 0 END) AS decisive_matches,
            SUM(CASE WHEN winner_id IS NULL OR UPPER(COALESCE(match_result, '')) = 'DRAW' THEN 1 ELSE 0 END) AS draws
        FROM ChessAdminApp_match
        """
    )

    outcomes = outcome_rows[0] if outcome_rows else {}
    decisive_matchesPy = int(outcomes.get("decisive_matches") or 0)
    drawsPy = int(outcomes.get("draws") or 0)

    return render_template(
        "index.html",
        users=usersPy,
        points_users=points_usersPy,
        total_members=total_membersPy,
        total_matches=total_matchesPy,
        top_player=top_playerPy,
        user_rank=user_rankPy,
        decisive_matches=decisive_matchesPy,
        draws=drawsPy,
        current_user_id=current_user_idPy,
    )


@app.route("/members")

def members():
    """Members list page."""
    print("BACKEND DEBUG: Received request to /members with user_id:", session.get("user_id"))

    users = db.execute(
        """
        SELECT
            cp.id,
            cp.first_name,
            cp.last_name,
            cp.city,
            cp.ranking AS rank,
            cp.points,
            cp.date_of_birth,
            au.email,
            au.username,
            COALESCE(au.date_joined, cp.date_joined) AS created_at
        FROM ChessAdminApp_player cp
        LEFT JOIN auth_user au ON cp.id = au.id
        ORDER BY cp.ranking ASC
        """
    )

    return render_template("members.html", users=users, current_user_id=session.get("user_id"))


@app.route("/addPlayer", methods=["POST"])
def add_player():
    """Create a new player from members page form data."""
    print("BACKEND DEBUG: Received request to /addPlayer with body:", request.form.to_dict())

    # Route action: Add Player -> POST /addPlayer.
    # Step 1: Read form data from members.html Add/Edit modal inputs.
    player_form_data = get_player_form_data(request.form)
    first_name = player_form_data["first_name"]
    last_name = player_form_data["last_name"]
    city = player_form_data["city"]
    ranking_raw = player_form_data["ranking_raw"]
    points_raw = player_form_data["points_raw"]
    date_of_birth = player_form_data["date_of_birth"]

    # Step 2: Validate required fields and numeric values.
    if is_empty(first_name, last_name):
        flash("First name and last name are required.", "error")
        return redirect("/members")

    try:
        ranking, points = parse_ranking_and_points(ranking_raw, points_raw)
    except ValueError:
        flash("Ranking and points must be valid integers.", "error")
        return redirect("/members")

    if ranking < 1:
        flash("Ranking must be at least 1.", "error")
        return redirect("/members")

    if points < 0:
        flash("Points cannot be negative.", "error")
        return redirect("/members")

    # Step 3: Keep rankings unique before inserting.
    # Add flow handling:
    # - clamp requested rank into valid add window 1..(count+1)
    # - shift players at/after that rank down
    # - insert new player at the safe rank
    try:
        safe_rank = shift_ranks_for_add(ranking, points)

        # Step 4: Insert player row in DB.
        db.execute(
            """
            INSERT INTO ChessAdminApp_player (first_name, last_name, city, ranking, points, date_of_birth, date_joined)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            first_name,
            last_name,
            city,
            safe_rank,
            points,
            date_of_birth,
        )

        normalize_rankings_with_ties()
        flash("Player added successfully.", "success")
    except Exception as exc:
        print("Add player error: {}".format(exc))
        flash("Could not add player.", "error")

    return redirect("/members")


@app.route("/editPlayer", methods=["POST"])
def edit_player():
    """Update an existing player by id from members page form data."""
    print("BACKEND DEBUG: Received request to /editPlayer with body:", request.form.to_dict())

    # Route action: Edit Player -> POST /editPlayer.
    # Step 1: Read playerId and form fields from members.html shared modal.
    # playerId is posted by hidden input name="id" and uniquely identifies the player record.
    player_id_raw = get_player_id_raw(request.form)
    player_form_data = get_player_form_data(request.form)
    first_name = player_form_data["first_name"]
    last_name = player_form_data["last_name"]
    city = player_form_data["city"]
    ranking_raw = player_form_data["ranking_raw"]
    points_raw = player_form_data["points_raw"]
    date_of_birth = player_form_data["date_of_birth"]

    if not player_id_raw:
        flash("Player id is required for update.", "error")
        return redirect("/members")

    # Step 2: Validate required fields and numeric values.
    if is_empty(first_name, last_name):
        flash("First name and last name are required.", "error")
        return redirect("/members")

    try:
        player_id = parse_player_id(player_id_raw)
        ranking, points = parse_ranking_and_points(ranking_raw, points_raw)
    except ValueError:
        flash("Player id, ranking, and points must be valid integers.", "error")
        return redirect("/members")

    if ranking < 1:
        flash("Ranking must be at least 1.", "error")
        return redirect("/members")

    if points < 0:
        flash("Points cannot be negative.", "error")
        return redirect("/members")

    # Step 3: Rebalance ranks around this player so the target rank stays unique.
    # playerId is used as the unique identifier for which row is being moved.
    # Edit flow handling:
    # - clamp requested rank into valid edit window 1..count
    # - move up to a better rank -> others shift down
    # - move down to a lower rank -> others shift up
    try:
        safe_rank = shift_ranks_for_edit(player_id, ranking, points)

        # Step 4: Update existing player row by unique id.
        db.execute(
            """
            UPDATE ChessAdminApp_player
            SET first_name = ?, last_name = ?, city = ?, ranking = ?, points = ?, date_of_birth = ?
            WHERE id = ?
            """,
            first_name,
            last_name,
            city,
            safe_rank,
            points,
            date_of_birth,
            player_id,
        )

        normalize_rankings_with_ties()
        flash("Player updated successfully.", "success")
    except Exception as exc:
        print("Edit player error: {}".format(exc))
        flash("Could not update player.", "error")

    return redirect("/members")


@app.route("/deletePlayer", methods=["POST"])
def delete_player():
    """Delete a player by id from members page."""
    print("BACKEND DEBUG: Received request to /deletePlayer with body:", request.form.to_dict())

    # Route action: Delete Player -> POST /deletePlayer.
    # Step 1: Read playerId from delete modal hidden input.
    player_id_raw = get_player_id_raw(request.form)
    if not player_id_raw:
        flash("Player id is required for deletion.", "error")
        return redirect("/members")

    # Step 2: Validate and parse unique player id.
    try:
        # playerId uniquely identifies the player record to remove.
        player_id = parse_player_id(player_id_raw)
    except ValueError:
        flash("Invalid player id.", "error")
        return redirect("/members")

    # Keep historical match integrity: do not delete players already referenced by matches.
    linked_match_rows = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM ChessAdminApp_match
        WHERE player_one_id = ?
           OR player_two_id = ?
           OR winner_id = ?
        """,
        player_id,
        player_id,
        player_id,
    )
    linked_match_count = int(linked_match_rows[0]["count"]) if linked_match_rows else 0
    if linked_match_count > 0:
        flash("Cannot delete player with recorded matches.", "error")
        return redirect("/members")

    # Step 3: Delete player row by id.
    try:
        db.execute("DELETE FROM ChessAdminApp_player WHERE id = ?", player_id)
        normalize_rankings_with_ties()
        flash("Player deleted successfully.", "success")
    except Exception as exc:
        print("Delete player error: {}".format(exc))
        flash("Could not delete player.", "error")

    return redirect("/members")


@app.route("/profile/<int:user_id>")
def profile(user_id):
    """Player profile page."""
    print(
        "BACKEND DEBUG: Received request to /profile/{} with current user_id:".format(user_id),
        session.get("user_id"),
    )

    user_rows = db.execute(
        """
        SELECT
            cp.id,
            cp.first_name,
            cp.last_name,
            cp.ranking AS rank,
            cp.points,
            cp.date_of_birth,
            au.email,
            au.username,
            au.last_login,
            au.date_joined AS created_at
        FROM ChessAdminApp_player cp
        LEFT JOIN auth_user au ON cp.id = au.id
        WHERE cp.id = ?
        """,
        user_id,
    )

    if not user_rows:
        return apology("User not found", 404)

    user = user_rows[0]
    user["created_at"] = normalize_datetime(user.get("created_at"))

    # Recent matches for this player.
    matches = db.execute(
        """
        SELECT
            m.*,
            CASE
                WHEN m.player_one_id = ? THEN cp2.first_name || ' ' || cp2.last_name
                ELSE cp1.first_name || ' ' || cp1.last_name
            END AS opponent_name,
            CASE
                WHEN m.player_one_id = ? THEN cp2.id
                ELSE cp1.id
            END AS opponent_id,
            m.scheduled_date AS played_at,
            m.player_one_entry_ranking AS p1_rank_before,
            (m.player_one_entry_ranking + m.player_one_ranking_change) AS p1_rank_after,
            m.player_two_entry_ranking AS p2_rank_before,
            (m.player_two_entry_ranking + m.player_two_ranking_change) AS p2_rank_after
        FROM ChessAdminApp_match m
        LEFT JOIN ChessAdminApp_player cp1 ON m.player_one_id = cp1.id
        LEFT JOIN ChessAdminApp_player cp2 ON m.player_two_id = cp2.id
        WHERE m.player_one_id = ? OR m.player_two_id = ?
        ORDER BY m.scheduled_date DESC
        LIMIT 10
        """,
        user_id,
        user_id,
        user_id,
        user_id,
    )

    wins = 0
    draws = 0
    losses = 0

    if matches:
        # Derive simple W/D/L summary from stored match result fields.
        for match_row in matches:
            match_result = (match_row.get("match_result") or "").lower()
            winner_id = match_row.get("winner_id")

            if winner_id is None or match_result == "draw":
                draws += 1
            elif winner_id == user_id:
                wins += 1
            else:
                losses += 1

    current_user_id = session.get("user_id")
    is_own_profile = current_user_id is not None and user_id == current_user_id

    return render_template(
        "profile.html",
        user=user,
        matches=matches,
        wins=wins,
        draws=draws,
        losses=losses,
        is_own_profile=is_own_profile,
        get_initials=get_initials,
        current_user_id=current_user_id,
    )


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    """Edit currently logged-in user's profile."""
    if not app.config.get("AUTH_PHASE_ENABLED", False):
        return apology("Edit profile is disabled for this phase.", 503)

    print(
        "BACKEND DEBUG: Received request to /edit_profile with user_id:",
        session.get("user_id"),
        "body:",
        request.form.to_dict(),
    )

    user_id = session["user_id"]

    # Query both player and auth data in one row for the edit form.
    user_rows = db.execute(
        """
        SELECT
            cp.id,
            cp.first_name,
            cp.last_name,
            cp.date_of_birth,
            au.email,
            au.username
        FROM ChessAdminApp_player cp
        LEFT JOIN auth_user au ON cp.id = au.id
        WHERE au.id = ?
        """,
        user_id,
    )

    if not user_rows:
        return apology("User not found", 404)

    user = user_rows[0]
    dob_value = normalize_datetime(user.get("date_of_birth"))
    user["date_of_birth"] = dob_value.strftime("%Y-%m-%d") if dob_value else user.get("date_of_birth")

    if request.method == "GET":
        return render_template("edit_profile.html", user=user)

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip()

    if not first_name:
        flash("First name is required.", "error")
        return render_template("edit_profile.html", user=user)

    if not last_name:
        flash("Last name is required.", "error")
        return render_template("edit_profile.html", user=user)

    if not email or not validate_email(email):
        flash("Valid email is required.", "error")
        return render_template("edit_profile.html", user=user)

    existing = db.execute("SELECT id FROM auth_user WHERE email = ? AND id != ?", email, user_id)
    if existing:
        flash("Email already in use.", "error")
        return render_template("edit_profile.html", user=user)

    try:
        # Keep auth and player names aligned by shared id.
        db.execute(
            "UPDATE auth_user SET first_name = ?, last_name = ?, email = ? WHERE id = ?",
            first_name,
            last_name,
            email,
            user_id,
        )
        db.execute(
            "UPDATE ChessAdminApp_player SET first_name = ?, last_name = ?, date_of_birth = ? WHERE id = ?",
            first_name,
            last_name,
            date_of_birth if date_of_birth else None,
            user_id,
        )

        flash("Profile updated successfully.", "success")
        return redirect("/profile/{}".format(user_id))
    except Exception as exc:
        print("Edit profile error: {}".format(exc))
        flash("An error occurred while updating profile.", "error")
        return render_template("edit_profile.html", user=user)


@app.route("/match", methods=["GET", "POST"])
def match():
    """Record a completed match without recalculating rankings."""
    print(
        "BACKEND DEBUG: Received request to /match with method:",
        request.method,
        "user_id:",
        session.get("user_id"),
        "body:",
        request.form.to_dict(),
    )

    if request.method == "GET":
        # Populate dropdowns with ranked players.
        players = db.execute(
            """
            SELECT
                cp.id,
                cp.first_name,
                cp.last_name,
                cp.ranking
            FROM ChessAdminApp_player cp
            ORDER BY cp.ranking ASC
            """
        )
        return render_template("match.html", users=players)

    try:
        player_one_id = int(request.form.get("player1_id", 0))
        player_two_id = int(request.form.get("player2_id", 0))
        result = request.form.get("result", "").strip()

        if player_one_id == player_two_id:
            flash("Players must be different.", "error")
            return redirect("/match")

        p1_rows = db.execute("SELECT * FROM ChessAdminApp_player WHERE id = ?", player_one_id)
        p2_rows = db.execute("SELECT * FROM ChessAdminApp_player WHERE id = ?", player_two_id)
        if not p1_rows or not p2_rows:
            flash("One or both players not found.", "error")
            return redirect("/match")

        if result not in ["p1", "draw", "p2"]:
            flash("Invalid result.", "error")
            return redirect("/match")

        p1 = p1_rows[0]
        p2 = p2_rows[0]

        if result == "p1":
            winner_id = player_one_id
        elif result == "p2":
            winner_id = player_two_id
        else:
            winner_id = None

        match_result = "DRAW" if result == "draw" else "WIN"

        # Ranking changes are intentionally disabled for now (teacher-led phase).
        player_one_ranking_change = 0
        player_two_ranking_change = 0

        # Insert completed match record (existing DB columns used only).
        db.execute(
            """
            INSERT INTO ChessAdminApp_match
                (scheduled_date, status, venue, match_result,
                 player_one_entry_ranking, player_two_entry_ranking,
                 player_one_ranking_change, player_two_ranking_change,
                 follow_live, player_one_id, player_two_id, winner_id,
                 player_one_points_change, player_two_points_change)
            VALUES (datetime('now'), 'COMPLETED', 'Chess Club', ?,
                    ?, ?, ?, ?,
                    'N/A', ?, ?, ?,
                    0, 0)
            """,
            match_result,
            p1["ranking"],
            p2["ranking"],
            player_one_ranking_change,
            player_two_ranking_change,
            player_one_id,
            player_two_id,
            winner_id,
        )

        flash("Match recorded.", "success")
        return redirect("/")
    except Exception as exc:
        print("Match recording error: {}".format(exc))
        flash("An error occurred while recording the match.", "error")
        return redirect("/match")


@app.route("/api/preview_match", methods=["POST"])
def api_preview_match():
    """Preview match participants without simulating ranking changes."""
    data = request.get_json(silent=True) or {}
    print(
        "BACKEND DEBUG: Received request to /api/preview_match with body:",
        data,
        "current user_id:",
        session.get("user_id"),
    )

    try:
        player_one_id = int(data.get("player1_id", 0))
        player_two_id = int(data.get("player2_id", 0))
        result = (data.get("result") or "").strip().lower()
        winner_id = data.get("winner_id")

        if not player_one_id or not player_two_id:
            return jsonify({"error": "Missing player IDs"}), 400

        if player_one_id == player_two_id:
            return jsonify({"error": "Players must be different"}), 400

        p1_rows = db.execute("SELECT * FROM ChessAdminApp_player WHERE id = ?", player_one_id)
        p2_rows = db.execute("SELECT * FROM ChessAdminApp_player WHERE id = ?", player_two_id)
        if not p1_rows or not p2_rows:
            return jsonify({"error": "Player not found"}), 404

        p1 = p1_rows[0]
        p2 = p2_rows[0]

        if result == "p1":
            winner_id = player_one_id
        elif result == "p2":
            winner_id = player_two_id
        elif result == "draw":
            winner_id = None
        elif winner_id is not None:
            winner_id = int(winner_id)
        else:
            winner_id = None

        return jsonify(
            {
                "p1_name": "{} {}".format(p1["first_name"], p1["last_name"]),
                "p2_name": "{} {}".format(p2["first_name"], p2["last_name"]),
                "p1_rank_before": p1["ranking"],
                "p1_rank_after": p1["ranking"],
                "p2_rank_before": p2["ranking"],
                "p2_rank_after": p2["ranking"],
                "p1_delta": 0,
                "p2_delta": 0,
            }
        )
    except Exception as exc:
        print("Preview match error: {}".format(exc))
        return jsonify({"error": str(exc)}), 400


@app.route("/history")
def history():
    """Match history page."""
    print("BACKEND DEBUG: Received request to /history with user_id:", session.get("user_id"))

    matches = db.execute(
        """
        SELECT
            m.*,
            m.scheduled_date AS played_at,
            m.player_one_entry_ranking AS p1_rank_before,
            (m.player_one_entry_ranking + m.player_one_ranking_change) AS p1_rank_after,
            m.player_two_entry_ranking AS p2_rank_before,
            (m.player_two_entry_ranking + m.player_two_ranking_change) AS p2_rank_after,
            cp1.first_name || ' ' || cp1.last_name AS player1_name,
            cp2.first_name || ' ' || cp2.last_name AS player2_name,
            cp1.id AS player1_id,
            cp2.id AS player2_id
        FROM ChessAdminApp_match m
        JOIN ChessAdminApp_player cp1 ON m.player_one_id = cp1.id
        JOIN ChessAdminApp_player cp2 ON m.player_two_id = cp2.id
        ORDER BY m.scheduled_date DESC
        """
    )

    if matches:
        # Build user-friendly result text used by history template.
        for match_row in matches:
            if match_row["winner_id"] is None:
                match_row["result"] = "Draw"
            elif match_row["winner_id"] == match_row["player1_id"]:
                match_row["result"] = "{} wins".format(match_row["player1_name"])
            else:
                match_row["result"] = "{} wins".format(match_row["player2_name"])

    return render_template("history.html", matches=matches)


@app.route("/test_db")
@login_required
def test_db():
    """Quick DB verification endpoint for migrated schema."""
    print("BACKEND DEBUG: Received request to /test_db")
    try:
        players = db.execute("SELECT * FROM ChessAdminApp_player LIMIT 5")
        matches = db.execute("SELECT * FROM ChessAdminApp_match LIMIT 3")
        users = db.execute("SELECT id, username, first_name, last_name FROM auth_user LIMIT 5")
        return jsonify(
            {
                "players": players,
                "matches": matches,
                "users": users,
                "status": "Connected to ChessAdmin.sqlite3 OK",
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "Connection failed"}), 500


# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    """500 error handler."""
    return render_template("500.html"), 500


# -----------------------------------------------------------------------------
# Local Development Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
