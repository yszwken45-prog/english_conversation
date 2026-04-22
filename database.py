import sqlite3
from datetime import date, timedelta

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
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            ai_tone TEXT DEFAULT 'フレンドリー',
            english_level TEXT DEFAULT '初級者',
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


def get_user_settings(user_id: int) -> dict:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT ai_tone, english_level FROM user_settings WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"ai_tone": "フレンドリー", "english_level": "初級者"}


def save_user_settings(user_id: int, ai_tone: str, english_level: str):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO user_settings (user_id, ai_tone, english_level) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET ai_tone = excluded.ai_tone, english_level = excluded.english_level",
        (user_id, ai_tone, english_level)
    )
    conn.commit()
    conn.close()


def get_dashboard_stats(user_id: int) -> dict:
    conn = get_db_connection()
    total_messages = conn.execute(
        "SELECT COUNT(*) FROM conversation_history WHERE user_id = ? AND role = 'user'",
        (user_id,)
    ).fetchone()[0]
    total_days = conn.execute(
        "SELECT COUNT(DISTINCT session_date) FROM conversation_history WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]
    mode_rows = conn.execute(
        "SELECT mode, COUNT(*) as cnt FROM conversation_history "
        "WHERE user_id = ? AND role = 'user' GROUP BY mode",
        (user_id,)
    ).fetchall()
    conn.close()
    messages_by_mode = {row["mode"]: row["cnt"] for row in mode_rows}
    return {
        "total_messages": total_messages,
        "total_days": total_days,
        "messages_by_mode": messages_by_mode,
    }


def get_daily_activity(user_id: int, days: int = 30) -> list:
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT session_date, COUNT(*) as cnt FROM conversation_history "
        "WHERE user_id = ? AND role = 'user' AND session_date >= ? "
        "GROUP BY session_date ORDER BY session_date ASC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [(row["session_date"], row["cnt"]) for row in rows]


def delete_user(user_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users_stats() -> list:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT u.id, u.username, u.created_at, "
        "COUNT(CASE WHEN c.role = 'user' THEN 1 END) as message_count, "
        "COUNT(DISTINCT c.session_date) as session_days "
        "FROM users u LEFT JOIN conversation_history c ON u.id = c.user_id "
        "GROUP BY u.id ORDER BY message_count DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
