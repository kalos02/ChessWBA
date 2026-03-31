import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_session import Session
from helpers import login_required, apply_ranking_rules, preview_ranking_rules, resequence_ranks, allowed_file, get_initials


class Database:
    """Simple SQLite wrapper to return results as list of dicts"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        
    def execute(self, query, *args):
        """Execute a query and return results as list of dicts"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, args)
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                results = cursor.fetchall()
                conn.close()
                return [dict(row) for row in results]
            else:
                conn.commit()
                conn.close()
                return None
        except Exception as e:
            conn.close()
            raise e


app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = "chess-club-secret-key-2024"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# Initialize session
Session(app)

# Initialize database
db = Database("chess.db")

# Initialize database schema on startup
def init_db():
    if not os.path.exists("chess.db"):
        conn = sqlite3.connect("chess.db")
        with open("schema.sql", "r") as f:
            schema = f.read()
            conn.executescript(schema)
        conn.close()

init_db()


@app.context_processor
def inject_helpers():
    """Make helper functions and current user available in all templates"""
    current_user = None
    if session.get("user_id"):
        result = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        current_user = result[0] if result else None
    return {
        'get_initials': get_initials,
        'current_user': current_user
    }


def apology(message, code=400):
    """Render apology template"""
    return render_template("apology.html", message=message), code


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@app.before_request
def before_request():
    """Create upload folder if it doesn't exist"""
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user"""
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirmation", "")

    # Validation
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

    # Check if username already exists
    existing = db.execute("SELECT id FROM users WHERE username = ?", username)
    if existing:
        flash("Username already exists.", "error")
        return render_template("register.html")

    # Check if email already exists
    existing = db.execute("SELECT id FROM users WHERE email = ?", email)
    if existing:
        flash("Email already exists.", "error")
        return render_template("register.html")

    # Assign initial rank based on user count
    result = db.execute("SELECT COUNT(*) as count FROM users")
    user_count = result[0]["count"] if result else 0
    initial_rank = user_count + 1

    # Insert new user
    try:
        hash_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, hash, email, first_name, last_name, rank) VALUES (?, ?, ?, ?, ?, ?)",
            username, hash_password, email, first_name, last_name, initial_rank
        )
        flash("Registered successfully! Please log in.", "success")
        return redirect("/login")
    except Exception as e:
        flash("An error occurred during registration.", "error")
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in a user"""
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

    # Look up user
    users = db.execute("SELECT * FROM users WHERE username = ?", username)
    if not users:
        flash("Invalid username or password.", "error")
        return render_template("login.html")

    user = users[0]

    # Check password
    if not check_password_hash(user["hash"], password):
        flash("Invalid username or password.", "error")
        return render_template("login.html")

    # Update last login and store session
    db.execute("UPDATE users SET last_login = ? WHERE id = ?", datetime.now().isoformat(), user["id"])
    session["user_id"] = user["id"]
    flash("Welcome back, {}!".format(user['first_name']), "success")
    return redirect("/")


@app.route("/logout")
def logout():
    """Log out the current user"""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/login")


@app.route("/")
@login_required
def index():
    """Home page - leaderboard view"""
    users = db.execute("SELECT * FROM users ORDER BY rank ASC")
    
    total_members = len(users) if users else 0
    result = db.execute("SELECT COUNT(*) as count FROM matches")
    total_matches = result[0]["count"] if result else 0
    top_player = users[0] if users else None
    
    current_user = db.execute("SELECT rank FROM users WHERE id = ?", session["user_id"])
    user_rank = current_user[0]["rank"] if current_user else 0

    return render_template(
        "index.html",
        users=users,
        total_members=total_members,
        total_matches=total_matches,
        top_player=top_player,
        user_rank=user_rank,
        current_user_id=session["user_id"]
    )


@app.route("/members")
@login_required
def members():
    """Members list page"""
    users = db.execute("SELECT * FROM users ORDER BY rank ASC")
    return render_template("members.html", users=users, current_user_id=session["user_id"])


@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    """User profile page"""
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    if not user:
        return apology("User not found", 404)

    user = user[0]

    # Convert created_at string to datetime object if needed
    if user.get("created_at") and isinstance(user["created_at"], str):
        try:
            user["created_at"] = datetime.strptime(user["created_at"], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            user["created_at"] = None

    # Get recent matches
    matches = db.execute(
        """
        SELECT m.*, 
               CASE 
                   WHEN m.player1_id = ? THEN u2.first_name || ' ' || u2.last_name
                   ELSE u1.first_name || ' ' || u1.last_name
               END as opponent_name,
               CASE
                   WHEN m.player1_id = ? THEN u2.id
                   ELSE u1.id
               END as opponent_id
        FROM matches m
        LEFT JOIN users u1 ON m.player1_id = u1.id
        LEFT JOIN users u2 ON m.player2_id = u2.id
        WHERE m.player1_id = ? OR m.player2_id = ?
        ORDER BY m.played_at DESC
        LIMIT 10
        """,
        user_id, user_id, user_id, user_id
    )

    # Calculate win/draw/loss
    wins = 0
    draws = 0
    losses = 0

    if matches:
        for match in matches:
            if match["winner_id"] is None:
                draws += 1
            elif match["winner_id"] == user_id:
                wins += 1
            else:
                losses += 1

    is_own_profile = (user_id == session["user_id"])

    return render_template(
        "profile.html",
        user=user,
        matches=matches,
        wins=wins,
        draws=draws,
        losses=losses,
        is_own_profile=is_own_profile,
        get_initials=get_initials,
        current_user_id=session["user_id"]
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit current user's profile"""
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    if not user:
        return apology("User not found", 404)
    
    user = user[0]

    if request.method == "GET":
        return render_template("edit_profile.html", user=user)

    # POST: update profile
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    birthday = request.form.get("birthday", "").strip()

    # Validation
    if not first_name:
        flash("First name is required.", "error")
        return render_template("edit_profile.html", user=user)

    if not last_name:
        flash("Last name is required.", "error")
        return render_template("edit_profile.html", user=user)

    if not email or not validate_email(email):
        flash("Valid email is required.", "error")
        return render_template("edit_profile.html", user=user)

    # Check if email already taken by another user
    existing = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", email, user_id)
    if existing:
        flash("Email already in use.", "error")
        return render_template("edit_profile.html", user=user)

    # Handle avatar upload
    avatar_filename = user["avatar_filename"]
    if "avatar" in request.files:
        file = request.files["avatar"]
        if file and file.filename and allowed_file(file.filename):
            # Delete old avatar if it exists
            if avatar_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], avatar_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            # Save new avatar
            filename = secure_filename(file.filename)
            filename = "{}_{}_{}" .format(user_id, datetime.now().timestamp(), filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            avatar_filename = filename
        elif file and file.filename:
            flash("Invalid file type. Only jpg, jpeg, png, and gif allowed.", "error")
            return render_template("edit_profile.html", user=user)

    # Update user
    try:
        db.execute(
            "UPDATE users SET first_name = ?, last_name = ?, email = ?, birthday = ?, avatar_filename = ? WHERE id = ?",
            first_name, last_name, email, birthday if birthday else None, avatar_filename, user_id
        )
        flash("Profile updated successfully.", "success")
        return redirect("/profile/{}".format(user_id))
    except Exception as e:
        flash("An error occurred while updating profile.", "error")
        return render_template("edit_profile.html", user=user)


@app.route("/match", methods=["GET", "POST"])
@login_required
def match():
    """Record a match"""
    if request.method == "GET":
        users = db.execute("SELECT * FROM users ORDER BY rank ASC")
        return render_template("match.html", users=users)

    # POST: record the match
    try:
        player1_id = int(request.form.get("player1_id", 0))
        player2_id = int(request.form.get("player2_id", 0))
        result = request.form.get("result", "").strip()

        # Validation
        if player1_id == player2_id:
            flash("Players must be different.", "error")
            return redirect("/match")

        p1 = db.execute("SELECT * FROM users WHERE id = ?", player1_id)
        p2 = db.execute("SELECT * FROM users WHERE id = ?", player2_id)

        if not p1 or not p2:
            flash("One or both players not found.", "error")
            return redirect("/match")

        if result not in ["p1", "draw", "p2"]:
            flash("Invalid result.", "error")
            return redirect("/match")

        p1 = p1[0]
        p2 = p2[0]

        # Determine winner
        if result == "p1":
            winner_id = player1_id
        elif result == "p2":
            winner_id = player2_id
        else:
            winner_id = None

        # Calculate new ranks
        new_p1_rank, new_p2_rank = apply_ranking_rules(
            {"id": player1_id, "rank": p1["rank"]},
            {"id": player2_id, "rank": p2["rank"]},
            winner_id
        )

        # Record match
        db.execute(
            """INSERT INTO matches 
               (player1_id, player2_id, winner_id, p1_rank_before, p2_rank_before, p1_rank_after, p2_rank_after)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            player1_id, player2_id, winner_id, p1["rank"], p2["rank"], new_p1_rank, new_p2_rank
        )

        # Update user ranks and games_played
        db.execute(
            "UPDATE users SET rank = ?, games_played = games_played + 1 WHERE id = ?",
            new_p1_rank, player1_id
        )
        db.execute(
            "UPDATE users SET rank = ?, games_played = games_played + 1 WHERE id = ?",
            new_p2_rank, player2_id
        )

        # Resequence all ranks to avoid gaps
        resequence_ranks(db)

        flash("Match recorded! Rankings updated.", "success")
        return redirect("/")

    except Exception as e:
        flash("An error occurred while recording the match.", "error")
        return redirect("/match")


@app.route("/api/preview_match", methods=["POST"])
@login_required
def api_preview_match():
    """API endpoint to preview ranking changes"""
    try:
        data = request.get_json()
        player1_id = data.get("player1_id")
        player2_id = data.get("player2_id")
        winner_id = data.get("winner_id")

        # Get players
        p1 = db.execute("SELECT * FROM users WHERE id = ?", player1_id)
        p2 = db.execute("SELECT * FROM users WHERE id = ?", player2_id)

        if not p1 or not p2:
            return jsonify({"error": "Player not found"}), 404

        p1 = p1[0]
        p2 = p2[0]

        # Determine winner position
        if winner_id is None:
            winner_position = "draw"
        elif winner_id == player1_id:
            winner_position = "p1"
        else:
            winner_position = "p2"

        # Preview new ranks
        new_p1_rank, new_p2_rank = preview_ranking_rules(
            p1["rank"], p2["rank"], winner_position
        )

        p1_delta = new_p1_rank - p1["rank"]
        p2_delta = new_p2_rank - p2["rank"]

        return jsonify({
            "p1_name": "{} {}".format(p1['first_name'], p1['last_name']),
            "p2_name": "{} {}".format(p2['first_name'], p2['last_name']),
            "p1_rank_before": p1["rank"],
            "p1_rank_after": new_p1_rank,
            "p2_rank_before": p2["rank"],
            "p2_rank_after": new_p2_rank,
            "p1_delta": p1_delta,
            "p2_delta": p2_delta
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/history")
@login_required
def history():
    """Match history page"""
    matches = db.execute(
        """
        SELECT m.*,
               u1.first_name || ' ' || u1.last_name as player1_name,
               u2.first_name || ' ' || u2.last_name as player2_name,
               u1.id as player1_id,
               u2.id as player2_id
        FROM matches m
        JOIN users u1 ON m.player1_id = u1.id
        JOIN users u2 ON m.player2_id = u2.id
        ORDER BY m.played_at DESC
        """
    )

    # Add result text to each match
    if matches:
        for match in matches:
            if match["winner_id"] is None:
                match["result"] = "Draw"
            elif match["winner_id"] == match["player1_id"]:
                match["result"] = "{} wins".format(match['player1_name'])
            else:
                match["result"] = "{} wins".format(match['player2_name'])

    return render_template("history.html", matches=matches)


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    """500 error handler"""
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
