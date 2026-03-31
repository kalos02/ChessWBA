from functools import wraps
from flask import session, redirect, flash
import math


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("You must be logged in to access this page.", "error")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def apply_ranking_rules(p1, p2, winner_id):
    """
    Apply ranking rules to determine new ranks.
    Returns tuple (new_p1_rank, new_p2_rank)
    
    Rules:
    - Lower rank number = better rank
    - Draw: if diff > 1, lower ranked player improves by 1
    - Upset win: if lower ranked wins, higher ranked += 1, lower ranked += floor(diff/2)
    """
    p1_rank = p1["rank"]
    p2_rank = p2["rank"]
    rank_diff = abs(p1_rank - p2_rank)
    
    if winner_id is None:
        # Draw
        if rank_diff > 1:
            if p1_rank > p2_rank:
                return (p1_rank - 1, p2_rank)
            else:
                return (p1_rank, p2_rank - 1)
        return (p1_rank, p2_rank)
    
    elif winner_id == p1["id"]:
        # Player 1 wins
        if p1_rank < p2_rank:
            # P1 is higher ranked (expected win)
            return (p1_rank, p2_rank - int(math.floor(rank_diff / 2)))
        else:
            # P1 is lower ranked (upset)
            return (p1_rank + int(math.floor(rank_diff / 2)), p2_rank + 1)
    
    else:
        # Player 2 wins
        if p2_rank < p1_rank:
            # P2 is higher ranked (expected win)
            return (p1_rank - int(math.floor(rank_diff / 2)), p2_rank)
        else:
            # P2 is lower ranked (upset)
            return (p1_rank + 1, p2_rank + int(math.floor(rank_diff / 2)))


def preview_ranking_rules(p1_rank, p2_rank, winner_position):
    """
    Preview ranking changes without modifying state.
    winner_position: 'p1', 'p2', or 'draw'
    Returns tuple (new_p1_rank, new_p2_rank)
    """
    rank_diff = abs(p1_rank - p2_rank)
    
    if winner_position == "draw":
        # Draw
        if rank_diff > 1:
            if p1_rank > p2_rank:
                return (p1_rank - 1, p2_rank)
            else:
                return (p1_rank, p2_rank - 1)
        return (p1_rank, p2_rank)
    
    elif winner_position == "p1":
        # Player 1 wins
        if p1_rank < p2_rank:
            # P1 is higher ranked (expected win)
            return (p1_rank, p2_rank - int(math.floor(rank_diff / 2)))
        else:
            # P1 is lower ranked (upset)
            return (p1_rank + int(math.floor(rank_diff / 2)), p2_rank + 1)
    
    else:  # winner_position == "p2"
        # Player 2 wins
        if p2_rank < p1_rank:
            # P2 is higher ranked (expected win)
            return (p1_rank - int(math.floor(rank_diff / 2)), p2_rank)
        else:
            # P2 is lower ranked (upset)
            return (p1_rank + 1, p2_rank + int(math.floor(rank_diff / 2)))


def resequence_ranks(db):
    """
    Normalize ranks after a match to avoid gaps.
    Sets ranks from 1 to N based on current rank order.
    """
    users = db.execute("SELECT id FROM users ORDER BY rank ASC")
    for i, user in enumerate(users, start=1):
        db.execute("UPDATE users SET rank = ? WHERE id = ?", i, user["id"])


def allowed_file(filename):
    """Check if file extension is allowed for avatars"""
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_initials(first_name, last_name):
    """Get 2-letter initials from names"""
    if not first_name or not last_name:
        return "U"
    return (first_name[0] + last_name[0]).upper()
