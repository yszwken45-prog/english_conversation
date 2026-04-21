import hashlib
import os
import sqlite3
import database


def _hash_password(password: str, salt: str = None):
    if salt is None:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return pwd_hash, salt


def register_user(username: str, password: str) -> bool:
    """Returns True if registration succeeded, False if username already exists."""
    pwd_hash, salt = _hash_password(password)
    conn = database.get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, pwd_hash, salt)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username: str, password: str):
    """Returns user_id if credentials are valid, None otherwise."""
    conn = database.get_db_connection()
    row = conn.execute(
        "SELECT id, password_hash, salt FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    pwd_hash, _ = _hash_password(password, row["salt"])
    if pwd_hash == row["password_hash"]:
        return row["id"]
    return None
