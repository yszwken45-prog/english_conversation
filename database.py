import sqlite3

DB_PATH = "app_data.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT DEFAULT '',
            mode TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def save_message(user_id: int, session_date: str, role: str, content: str, mode: str):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO conversation_history (user_id, session_date, role, content, mode) VALUES (?, ?, ?, ?, ?)",
        (user_id, session_date, role, content or "", mode or "")
    )
    conn.commit()
    conn.close()


def load_messages_by_date(user_id: int, session_date: str) -> list:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT role, content, mode FROM conversation_history WHERE user_id = ? AND session_date = ? ORDER BY id ASC",
        (user_id, session_date)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_session_dates(user_id: int) -> list:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DISTINCT session_date FROM conversation_history WHERE user_id = ? ORDER BY session_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]
