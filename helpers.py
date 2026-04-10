# -*- coding: utf-8 -*-
"""
ChessWBA helper utilities (backend)

Purpose:
- login_required decorator for protecting endpoints
- ranking rules logic for match outcomes and rank updates
- utility functions for avatar file handling and initials

Connections:
- Used by `app.py` for auth checks and match calculations
"""

from functools import wraps
from flask import redirect, session

# -----------------------------------------------------------------------------
# Authentication Helper
# -----------------------------------------------------------------------------
def login_required(f):
    """Redirect anonymous users to login before protected views."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")   
        return f(*args, **kwargs)
    return decorated_function


# -----------------------------------------------------------------------------
# Ranking Rules
# -----------------------------------------------------------------------------
def preview_ranking_rules(p1_rank, p2_rank, winner_position):
    """
    Exact ranking rules as per the Netstock assignment:
    - Higher-ranked player = lower rank number
    - If higher wins -> no change
    - Draw -> lower-ranked gains 1 position (unless adjacent)
    - Lower beats higher -> higher moves down 1, lower moves up by floor(diff/2)
    """
    if p1_rank < p2_rank:
        higher_rank = p1_rank
        lower_rank = p2_rank
        p1_is_higher = True
    else:
        higher_rank = p2_rank
        lower_rank = p1_rank
        p1_is_higher = False

    diff = lower_rank - higher_rank

    if winner_position == "draw":
        if diff > 1:
            new_lower = lower_rank - 1
            new_higher = higher_rank
        else:
            new_lower = lower_rank
            new_higher = higher_rank

    elif winner_position == "p1":          # Player 1 wins
        if p1_is_higher:
            # Higher-ranked wins -> no change
            new_higher = higher_rank
            new_lower = lower_rank
        else:
            # Lower-ranked (p1) upsets higher-ranked (p2)
            new_higher = higher_rank + 1
            new_lower = lower_rank - (diff // 2)

    else:  # winner_position == "p2" -> Player 2 wins
        if not p1_is_higher:
            # Higher-ranked wins -> no change
            new_higher = higher_rank
            new_lower = lower_rank
        else:
            # Lower-ranked (p2) upsets higher-ranked (p1)
            new_higher = higher_rank + 1
            new_lower = lower_rank - (diff // 2)

    # Return new ranks in original order (p1, p2)
    if p1_is_higher:
        return new_higher, new_lower
    else:
        return new_lower, new_higher


def apply_ranking_rules(p1, p2, winner_id):
    """Resolve winner side and apply ranking rules for persisted matches."""
    if winner_id == p1["id"]:
        pos = "p1"
    elif winner_id == p2["id"]:
        pos = "p2"
    else:
        pos = "draw"
    
    return preview_ranking_rules(p1["rank"], p2["rank"], pos)


def resequence_ranks(db):
    """Renumber all ranks from 1 to n with no gaps after changes"""
    rows = db.execute("SELECT id FROM ChessAdminApp_player ORDER BY ranking ASC")
    for i, row in enumerate(rows, start=1):
        db.execute("UPDATE ChessAdminApp_player SET ranking = ? WHERE id = ?", i, row["id"])


# -----------------------------------------------------------------------------
# Misc Utility Helpers
# -----------------------------------------------------------------------------
def allowed_file(filename):
    """Allow only image file extensions used by profile uploads."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"jpg", "jpeg", "png", "gif"}


def get_initials(first_name, last_name):
    """Return up to two initials for avatar placeholders."""
    fn = first_name[0].upper() if first_name else ""
    ln = last_name[0].upper() if last_name else ""
    return (fn + ln)[:2]