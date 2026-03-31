CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birthday TEXT,
    games_played INTEGER NOT NULL DEFAULT 0,
    rank INTEGER NOT NULL,
    avatar_filename TEXT DEFAULT NULL,
    last_login TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL REFERENCES users(id),
    player2_id INTEGER NOT NULL REFERENCES users(id),
    winner_id INTEGER REFERENCES users(id),
    p1_rank_before INTEGER NOT NULL,
    p2_rank_before INTEGER NOT NULL,
    p1_rank_after INTEGER NOT NULL,
    p2_rank_after INTEGER NOT NULL,
    played_at TEXT NOT NULL DEFAULT (datetime('now'))
);
