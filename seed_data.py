"""サンプルユーザーと会話履歴を DB に投入するスクリプト"""
import random
from datetime import date, timedelta
import database
import auth

database.init_db()

USERS = [
    ("admin",   "admin123"),
    ("alice",   "pass1234"),
    ("bob",     "pass1234"),
    ("carol",   "pass1234"),
    ("dave",    "pass1234"),
]

MODES = ["日常英会話", "シャドーイング", "ディクテーション"]

AI_MESSAGES = [
    "Hello! How are you doing today?",
    "That's great! Can you tell me more about your day?",
    "Excellent pronunciation! Let's try the next sentence.",
    "Good job! Your answer was very natural.",
    "Let's practice a bit more. Repeat after me.",
    "Nice work! You're improving quickly.",
    "Try to speak a little slower and more clearly.",
    "Perfect! That was exactly right.",
]

USER_MESSAGES = [
    "I'm doing fine, thank you.",
    "Today was a pretty busy day at work.",
    "I went to the supermarket after work.",
    "I think I need more practice with pronunciation.",
    "Can we try a different topic?",
    "I understood most of it this time.",
    "That was difficult but I'll keep trying.",
    "Thank you for the feedback.",
]

TODAY = date.today()

def random_messages(mode: str, count: int):
    msgs = []
    for _ in range(count):
        msgs.append(("assistant", random.choice(AI_MESSAGES), mode))
        msgs.append(("user", random.choice(USER_MESSAGES), mode))
    return msgs

# --- ユーザー登録 ---
user_ids = {}
for username, password in USERS:
    ok = auth.register_user(username, password)
    status = "登録済み" if ok else "既存"
    print(f"  {username}: {status}")
    conn = database.get_db_connection()
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    user_ids[username] = row["id"]

# --- 会話履歴生成 ---
# 各ユーザーに異なる学習パターンを割り当てる
patterns = {
    "admin":  {"days": 5,  "max_msgs": 3, "mode_weights": [5, 3, 2]},
    "alice":  {"days": 28, "max_msgs": 8, "mode_weights": [6, 2, 2]},
    "bob":    {"days": 20, "max_msgs": 5, "mode_weights": [3, 5, 2]},
    "carol":  {"days": 15, "max_msgs": 6, "mode_weights": [2, 3, 5]},
    "dave":   {"days": 10, "max_msgs": 4, "mode_weights": [4, 3, 3]},
}

conn = database.get_db_connection()
for username, pat in patterns.items():
    uid = user_ids[username]
    active_days = sorted(random.sample(range(30), min(pat["days"], 30)))
    for offset in active_days:
        session_date = (TODAY - timedelta(days=29 - offset)).isoformat()
        mode = random.choices(MODES, weights=pat["mode_weights"])[0]
        msg_count = random.randint(2, pat["max_msgs"])
        for role, content, m in random_messages(mode, msg_count):
            conn.execute(
                "INSERT INTO conversation_history (user_id, session_date, role, content, mode) VALUES (?, ?, ?, ?, ?)",
                (uid, session_date, role, content, m)
            )
    print(f"  {username}: {len(active_days)} 日分の履歴を追加")

conn.commit()
conn.close()

print("\n完了！サンプルデータの投入が終わりました。")
print("ログイン情報:")
for username, password in USERS:
    print(f"  {username} / {password}")
