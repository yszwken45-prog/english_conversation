import streamlit as st
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from time import sleep
from pathlib import Path
from datetime import date
from streamlit.components.v1 import html
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import pandas as pd
import functions as ft
import constants as ct
import database
import auth


# ログ設定
os.makedirs("logs", exist_ok=True)
_log_handler = RotatingFileHandler(
    "logs/app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.WARNING)

# 各種設定
load_dotenv()
st.set_page_config(
    page_title=ct.APP_NAME
)

# DB初期化
database.init_db()

# ログイン状態の初期化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.current_page = "main"

# ─── ログイン画面 ───────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown(f"## {ct.APP_NAME}")
    st.markdown("### ログイン / 新規登録")
    tab_login, tab_register = st.tabs(["ログイン", "新規登録"])

    with tab_login:
        login_username = st.text_input("ユーザー名", key="login_username")
        login_password = st.text_input("パスワード", type="password", key="login_password")
        if st.button("ログイン", type="primary", key="btn_login"):
            user_id = auth.verify_user(login_username, login_password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = login_username
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません")

    with tab_register:
        reg_username = st.text_input("ユーザー名（2文字以上）", key="reg_username")
        reg_password = st.text_input("パスワード（6文字以上）", type="password", key="reg_password")
        reg_password2 = st.text_input("パスワード（確認）", type="password", key="reg_password2")
        if st.button("登録", type="primary", key="btn_register"):
            if reg_password != reg_password2:
                st.error("パスワードが一致しません")
            elif len(reg_username) < 2:
                st.error("ユーザー名は2文字以上で入力してください")
            elif len(reg_password) < 6:
                st.error("パスワードは6文字以上で入力してください")
            elif auth.register_user(reg_username, reg_password):
                st.success("登録が完了しました。「ログイン」タブからログインしてください。")
            else:
                st.error("このユーザー名はすでに使用されています")

    st.stop()

# ─── サイドバー（ログイン済み） ──────────────────────────────
with st.sidebar:
    st.markdown(f"### ようこそ、{st.session_state.username} さん")

    st.markdown("#### ナビゲーション")
    _page_map = {"学習": "main", "ダッシュボード": "dashboard", "設定": "settings"}
    if st.session_state.username == ct.ADMIN_USERNAME:
        _page_map["管理者"] = "admin"
    for _label, _key in _page_map.items():
        _btn_type = "primary" if st.session_state.current_page == _key else "secondary"
        if st.button(_label, key=f"nav_{_key}", use_container_width=True, type=_btn_type):
            st.session_state.current_page = _key
            st.rerun()

    st.divider()
    if st.button("ログアウト", key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    if st.session_state.current_page == "main":
        st.divider()
        st.markdown("### 学習履歴")
        session_dates = database.get_session_dates(st.session_state.user_id)
        if session_dates:
            selected_date = st.selectbox("日付", session_dates, label_visibility="collapsed")
            if st.button("この日の履歴を表示", key="btn_show_history"):
                st.session_state.history_to_show = selected_date

            if st.session_state.get("history_to_show"):
                hist_msgs = database.load_messages_by_date(
                    st.session_state.user_id, st.session_state.history_to_show
                )
                with st.expander(f"{st.session_state.history_to_show} の記録", expanded=True):
                    for m in hist_msgs:
                        if m["role"] == "assistant":
                            st.markdown(f"**AI:** {m['content']}")
                        elif m["role"] == "user":
                            st.markdown(f"**あなた:** {m['content']}")
                        else:
                            st.markdown("---")
        else:
            st.info("まだ履歴がありません")

    st.divider()
    st.caption(f"v{ct.VERSION}")


def _append_and_save(role: str, content: str = ""):
    """メッセージをsession_stateとDBの両方に追加する"""
    msg = {"role": role, "content": content} if role != "other" else {"role": "other"}
    st.session_state.messages.append(msg)
    database.save_message(
        st.session_state.user_id,
        st.session_state.session_date,
        role,
        content,
        st.session_state.get("mode", "")
    )


def _render_dashboard():
    st.markdown(f"## {ct.APP_NAME}")
    st.markdown("### ダッシュボード")
    stats = database.get_dashboard_stats(st.session_state.user_id)
    by_mode = stats["messages_by_mode"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総会話数", stats["total_messages"])
    with col2:
        st.metric("学習日数", stats["total_days"])
    with col3:
        best_mode = max(by_mode, key=by_mode.get) if by_mode else "—"
        st.metric("最多使用モード", best_mode)

    st.divider()
    st.markdown("#### 直近30日の学習活動")
    activity = database.get_daily_activity(st.session_state.user_id, days=30)
    if activity:
        df = pd.DataFrame(activity, columns=["日付", "会話数"]).set_index("日付")
        st.bar_chart(df)
    else:
        st.info("まだ学習記録がありません")

    st.divider()
    st.markdown("#### モード別利用状況")
    mode_data = {k: v for k, v in by_mode.items() if k}
    if mode_data:
        df_mode = pd.DataFrame.from_dict(mode_data, orient="index", columns=["回数"])
        st.bar_chart(df_mode)
    else:
        st.info("まだ学習記録がありません")


def _render_settings():
    st.markdown(f"## {ct.APP_NAME}")
    st.markdown("### プロフィール設定")
    saved = database.get_user_settings(st.session_state.user_id)

    st.markdown("#### AIのパーソナライズ")
    _tone_idx = ct.AI_TONE_OPTIONS.index(saved["ai_tone"]) if saved["ai_tone"] in ct.AI_TONE_OPTIONS else 0
    ai_tone = st.selectbox("AIの話し方", ct.AI_TONE_OPTIONS, index=_tone_idx)
    _tone_desc = {
        "フレンドリー": "フレンドリーでカジュアルな話し方。日常英会話の練習に最適です。",
        "フォーマル": "丁寧でフォーマルな話し方。礼儀正しいコミュニケーションの練習に最適です。",
        "ビジネス": "ビジネス英語を意識した話し方。職場でのコミュニケーション練習に最適です。",
    }
    st.caption(_tone_desc.get(ai_tone, ""))

    st.markdown("#### デフォルト英語レベル")
    _lvl_idx = ct.ENGLISH_LEVEL_OPTION.index(saved["english_level"]) if saved["english_level"] in ct.ENGLISH_LEVEL_OPTION else 0
    english_level = st.selectbox("英語レベル", ct.ENGLISH_LEVEL_OPTION, index=_lvl_idx)

    if st.button("設定を保存", type="primary"):
        database.save_user_settings(st.session_state.user_id, ai_tone, english_level)
        st.session_state.ai_tone = ai_tone
        st.session_state.default_english_level = english_level
        tone_suffix = ct.AI_TONE_PROMPT_SUFFIX.get(ai_tone, "")
        st.session_state.chain_basic_conversation = ft.create_chain(
            ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION + tone_suffix
        )
        st.success("設定を保存しました。AIの話し方が次の会話から反映されます。")

    st.divider()
    st.markdown("#### パスワード変更")
    current_pw = st.text_input("現在のパスワード", type="password", key="current_pw")
    new_pw = st.text_input("新しいパスワード", type="password", key="new_pw")
    new_pw2 = st.text_input("新しいパスワード（確認）", type="password", key="new_pw2")
    if st.button("パスワードを変更", key="btn_change_pw"):
        if not current_pw or not new_pw:
            st.error("すべての項目を入力してください")
        elif new_pw != new_pw2:
            st.error("新しいパスワードが一致しません")
        elif len(new_pw) < 4:
            st.error("パスワードは4文字以上にしてください")
        elif auth.change_password(st.session_state.user_id, current_pw, new_pw):
            st.success("パスワードを変更しました")
        else:
            st.error("現在のパスワードが正しくありません")


def _render_admin():
    if st.session_state.username != ct.ADMIN_USERNAME:
        st.error("このページへのアクセス権限がありません")
        return
    st.markdown(f"## {ct.APP_NAME}")
    st.markdown("### 管理者ページ")
    users = database.get_all_users_stats()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("総ユーザー数", len(users))
    with col2:
        st.metric("総メッセージ数", sum(u["message_count"] for u in users))

    st.divider()
    st.markdown("#### ユーザー一覧")
    if users:
        for u in users:
            col_name, col_info, col_del = st.columns([2, 4, 1])
            with col_name:
                st.write(u["username"])
            with col_info:
                st.caption(f"登録: {u['created_at'][:10]}　会話: {u['message_count']}回　学習: {u['session_days']}日")
            with col_del:
                if u["username"] != st.session_state.username:
                    if st.button("削除", key=f"del_{u['id']}", type="secondary"):
                        database.delete_user(u["id"])
                        st.success(f"{u['username']} を削除しました")
                        st.rerun()
    else:
        st.info("登録ユーザーがいません")

    st.divider()
    st.markdown("#### サンプルデータ")
    st.caption("alice / bob / carol / dave をサンプルユーザーとして追加します（パスワード: pass1234）")
    if st.button("サンプルデータを投入", key="btn_seed"):
        import random
        from datetime import timedelta
        SAMPLE_USERS = [("alice", "pass1234"), ("bob", "pass1234"), ("carol", "pass1234"), ("dave", "pass1234")]
        MODES = ["日常英会話", "シャドーイング", "ディクテーション"]
        AI_MSGS = ["Hello! How are you doing today?", "That's great! Can you tell me more?",
                   "Excellent! Let's try the next sentence.", "Good job! Very natural.",
                   "Let's practice a bit more.", "Nice work! You're improving quickly."]
        USER_MSGS = ["I'm doing fine, thank you.", "Today was a busy day.",
                     "I went to the supermarket.", "I need more practice.",
                     "Can we try a different topic?", "I understood most of it."]
        patterns = {
            "alice": {"days": 28, "max_msgs": 8, "weights": [6, 2, 2]},
            "bob":   {"days": 20, "max_msgs": 5, "weights": [3, 5, 2]},
            "carol": {"days": 15, "max_msgs": 6, "weights": [2, 3, 5]},
            "dave":  {"days": 10, "max_msgs": 4, "weights": [4, 3, 3]},
        }
        today = date.today()
        added = []
        for username, password in SAMPLE_USERS:
            ok = auth.register_user(username, password)
            if not ok:
                continue
            conn = database.get_db_connection()
            uid = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()["id"]
            pat = patterns[username]
            active_days = sorted(random.sample(range(30), pat["days"]))
            for offset in active_days:
                session_date = (today - timedelta(days=29 - offset)).isoformat()
                mode = random.choices(MODES, weights=pat["weights"])[0]
                for _ in range(random.randint(2, pat["max_msgs"])):
                    conn.execute(
                        "INSERT INTO conversation_history (user_id, session_date, role, content, mode) VALUES (?, ?, ?, ?, ?)",
                        (uid, session_date, "assistant", random.choice(AI_MSGS), mode)
                    )
                    conn.execute(
                        "INSERT INTO conversation_history (user_id, session_date, role, content, mode) VALUES (?, ?, ?, ?, ?)",
                        (uid, session_date, "user", random.choice(USER_MSGS), mode)
                    )
            conn.commit()
            conn.close()
            added.append(username)
        if added:
            st.success(f"追加しました: {', '.join(added)}")
            st.rerun()
        else:
            st.info("追加できるサンプルユーザーがいません（すでに登録済みの可能性があります）")


# ─── ページルーティング ─────────────────────────────────────
if st.session_state.current_page == "dashboard":
    _render_dashboard()
    st.stop()
elif st.session_state.current_page == "settings":
    _render_settings()
    st.stop()
elif st.session_state.current_page == "admin":
    _render_admin()
    st.stop()

# タイトル表示
st.markdown(f"## {ct.APP_NAME}")

# 初期処理
if "messages" not in st.session_state:
    st.session_state.session_date = str(date.today())
    st.session_state.start_flg = False
    st.session_state.pre_mode = ""
    st.session_state.shadowing_flg = False
    st.session_state.shadowing_button_flg = False
    st.session_state.shadowing_count = 0
    st.session_state.shadowing_first_flg = True
    st.session_state.shadowing_audio_input_flg = False
    st.session_state.shadowing_evaluation_first_flg = True
    st.session_state.dictation_flg = False
    st.session_state.dictation_button_flg = False
    st.session_state.dictation_count = 0
    st.session_state.dictation_first_flg = True
    st.session_state.dictation_chat_message = ""
    st.session_state.dictation_evaluation_first_flg = True
    st.session_state.chat_open_flg = False
    st.session_state.problem = ""

    st.session_state.openai_obj = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    st.session_state.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
    st.session_state.memory = ConversationSummaryBufferMemory(
        llm=st.session_state.llm,
        max_token_limit=1000,
        return_messages=True
    )

    # ユーザー設定の読み込み
    _user_settings = database.get_user_settings(st.session_state.user_id)
    st.session_state.ai_tone = _user_settings["ai_tone"]
    st.session_state.default_english_level = _user_settings["english_level"]

    # モード「日常英会話」用のChain作成（AIトーン設定を反映）
    _tone_suffix = ct.AI_TONE_PROMPT_SUFFIX.get(st.session_state.ai_tone, "")
    st.session_state.chain_basic_conversation = ft.create_chain(ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION + _tone_suffix)

    # 今日の履歴をDBから読み込む
    today_history = database.load_messages_by_date(st.session_state.user_id, st.session_state.session_date)
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"]} if m["role"] != "other"
        else {"role": "other"}
        for m in today_history
    ]

# 初期表示
# col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
# 提出課題用
col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
with col1:
    if st.session_state.start_flg:
        st.button("開始", use_container_width=True, type="primary")
    else:
        st.session_state.start_flg = st.button("開始", use_container_width=True, type="primary")
with col2:
    st.session_state.speed = st.selectbox(label="再生速度", options=ct.PLAY_SPEED_OPTION, index=3, label_visibility="collapsed")
with col3:
    st.session_state.mode = st.selectbox(label="モード", options=[ct.MODE_1, ct.MODE_2, ct.MODE_3], label_visibility="collapsed")
    # モードを変更した際の処理
    if st.session_state.mode != st.session_state.pre_mode:
        # 自動でそのモードの処理が実行されないようにする
        st.session_state.start_flg = False
        # 「日常英会話」選択時の初期化処理
        if st.session_state.mode == ct.MODE_1:
            st.session_state.dictation_flg = False
            st.session_state.shadowing_flg = False
        # 「シャドーイング」選択時の初期化処理
        st.session_state.shadowing_count = 0
        if st.session_state.mode == ct.MODE_2:
            st.session_state.dictation_flg = False
        # 「ディクテーション」選択時の初期化処理
        st.session_state.dictation_count = 0
        if st.session_state.mode == ct.MODE_3:
            st.session_state.shadowing_flg = False
        # チャット入力欄を非表示にする
        st.session_state.chat_open_flg = False
    st.session_state.pre_mode = st.session_state.mode
with col4:
    _default_lvl_idx = ct.ENGLISH_LEVEL_OPTION.index(st.session_state.get("default_english_level", "初級者"))
    st.session_state.englv = st.selectbox(label="英語レベル", options=ct.ENGLISH_LEVEL_OPTION, index=_default_lvl_idx, label_visibility="collapsed")

with st.chat_message("assistant", avatar="images/ai_icon.jpg"):
    st.markdown("こちらは生成AIによる音声英会話の練習アプリです。何度も繰り返し練習し、英語力をアップさせましょう。")
    st.markdown("**【操作説明】**")
    st.success("""
    - モードと再生速度を選択し、「英会話開始」ボタンを押して英会話を始めましょう。
    - モードは「日常英会話」「シャドーイング」「ディクテーション」から選べます。
    - 発話後、5秒間沈黙することで音声入力が完了します。
    - 「一時中断」ボタンを押すことで、英会話を一時中断できます。
    """)
st.divider()

# メッセージリストの一覧表示
for message in st.session_state.messages:
    if message["role"] == "assistant":
        with st.chat_message(message["role"], avatar="images/ai_icon.jpg"):
            st.markdown(message["content"])
    elif message["role"] == "user":
        with st.chat_message(message["role"], avatar="images/user_icon.jpg"):
            st.markdown(message["content"])
    else:
        st.divider()

# LLMレスポンスの下部にモード実行のボタン表示
if st.session_state.shadowing_flg:
    st.session_state.shadowing_button_flg = st.button("シャドーイング開始")
if st.session_state.dictation_flg:
    st.session_state.dictation_button_flg = st.button("ディクテーション開始")

# 「ディクテーション」モードのチャット入力受付時に実行
if st.session_state.chat_open_flg:
    st.info("AIが読み上げた音声を、画面下部のチャット欄からそのまま入力・送信してください。")

st.session_state.dictation_chat_message = st.chat_input("※「ディクテーション」選択時以外は送信不可")

if st.session_state.dictation_chat_message and not st.session_state.chat_open_flg:
    st.stop()

# 「英会話開始」ボタンが押された場合の処理
if st.session_state.start_flg:

    # モード：「ディクテーション」
    # 「ディクテーション」ボタン押下時か、「英会話開始」ボタン押下時か、チャット送信時
    if st.session_state.mode == ct.MODE_3 and (st.session_state.dictation_button_flg or st.session_state.dictation_count == 0 or st.session_state.dictation_chat_message):
        if st.session_state.dictation_first_flg:
            st.session_state.chain_create_problem = ft.create_chain(ct.SYSTEM_TEMPLATE_CREATE_PROBLEM)
            st.session_state.dictation_first_flg = False
        # チャット入力以外
        if not st.session_state.chat_open_flg:
            with st.spinner('問題文生成中...'):
                st.session_state.problem, llm_response_audio = ft.create_problem_and_play_audio()

            st.session_state.chat_open_flg = True
            st.session_state.dictation_flg = False
    
        # チャット入力時の処理
        else:
            # チャット欄から入力された場合にのみ評価処理が実行されるようにする
            if not st.session_state.dictation_chat_message:
                st.stop()
            
            # AIメッセージとユーザーメッセージの画面表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(st.session_state.problem)
            with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                st.markdown(st.session_state.dictation_chat_message)

            # LLMが生成した問題文とチャット入力値をメッセージリストに追加
            _append_and_save("assistant", st.session_state.problem)
            _append_and_save("user", st.session_state.dictation_chat_message)
            
            with st.spinner('評価結果の生成中...'):
                system_template = ct.SYSTEM_TEMPLATE_EVALUATION.format(
                    llm_text=st.session_state.problem,
                    user_text=st.session_state.dictation_chat_message
                )
                st.session_state.chain_evaluation = ft.create_chain(system_template)
                # 問題文と回答を比較し、評価結果の生成を指示するプロンプトを作成
                llm_response_evaluation = ft.create_evaluation()
            
            # 評価結果のメッセージリストへの追加と表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(llm_response_evaluation)
            _append_and_save("assistant", llm_response_evaluation)
            _append_and_save("other")

            # 各種フラグの更新
            st.session_state.dictation_flg = True
            st.session_state.dictation_chat_message = ""
            st.session_state.dictation_count += 1
            st.session_state.chat_open_flg = False

            st.rerun()

    
    # モード：「日常英会話」
    if st.session_state.mode == ct.MODE_1:
        # 音声入力を受け取って音声ファイルを作成
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        audio_data = ft.record_audio(audio_input_file_path)

        # 音声入力ファイルから文字起こしテキストを取得
        with st.spinner('音声入力をテキストに変換中...'):
            transcript = ft.transcribe_audio(audio_input_file_path)
            audio_input_text = transcript.text

        # 音声入力テキストの画面表示
        with st.chat_message("user", avatar=ct.USER_ICON_PATH):
            st.markdown(audio_input_text)

        with st.spinner("回答の音声読み上げ準備中..."):
            # ユーザー入力値をLLMに渡して回答取得
            llm_response = st.session_state.chain_basic_conversation.predict(input=audio_input_text)
            
            # LLMからの回答を音声データに変換
            llm_response_audio = st.session_state.openai_obj.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=llm_response
            )

            # 一旦mp3形式で音声ファイル作成後、wav形式に変換
            audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
            ft.save_to_wav(llm_response_audio.content, audio_output_file_path)

        # 音声ファイルの読み上げ
        ft.play_wav(audio_output_file_path, speed=st.session_state.speed)

        # AIメッセージの画面表示とリストへの追加
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response)

        # ユーザー入力値とLLMからの回答をメッセージ一覧に追加
        _append_and_save("user", audio_input_text)
        _append_and_save("assistant", llm_response)


    # モード：「シャドーイング」
    # 「シャドーイング」ボタン押下時か、「英会話開始」ボタン押下時
    if st.session_state.mode == ct.MODE_2 and (st.session_state.shadowing_button_flg or st.session_state.shadowing_count == 0 or st.session_state.shadowing_audio_input_flg):
        if st.session_state.shadowing_first_flg:
            st.session_state.chain_create_problem = ft.create_chain(ct.SYSTEM_TEMPLATE_CREATE_PROBLEM)
            st.session_state.shadowing_first_flg = False
        
        if not st.session_state.shadowing_audio_input_flg:
            with st.spinner('問題文生成中...'):
                st.session_state.problem, llm_response_audio = ft.create_problem_and_play_audio()

        # 音声入力を受け取って音声ファイルを作成
        st.session_state.shadowing_audio_input_flg = True
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        ft.record_audio(audio_input_file_path)
        st.session_state.shadowing_audio_input_flg = False

        with st.spinner('音声入力をテキストに変換中...'):
            # 音声入力ファイルから文字起こしテキストを取得
            transcript = ft.transcribe_audio(audio_input_file_path)
            audio_input_text = transcript.text

        # AIメッセージとユーザーメッセージの画面表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(st.session_state.problem)
        with st.chat_message("user", avatar=ct.USER_ICON_PATH):
            st.markdown(audio_input_text)
        
        # LLMが生成した問題文と音声入力値をメッセージリストに追加
        _append_and_save("assistant", st.session_state.problem)
        _append_and_save("user", audio_input_text)

        with st.spinner('評価結果の生成中...'):
            if st.session_state.shadowing_evaluation_first_flg:
                system_template = ct.SYSTEM_TEMPLATE_EVALUATION_SHADOWING.format(
                    llm_text=st.session_state.problem,
                    user_text=audio_input_text
                )
                st.session_state.chain_evaluation = ft.create_chain(system_template)
                st.session_state.shadowing_evaluation_first_flg = False
            # 問題文と回答を比較し、評価結果の生成を指示するプロンプトを作成
            llm_response_evaluation = ft.create_evaluation()
        
        # 評価結果のメッセージリストへの追加と表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response_evaluation)
        _append_and_save("assistant", llm_response_evaluation)
        _append_and_save("other")

        # 各種フラグの更新
        st.session_state.shadowing_flg = True
        st.session_state.shadowing_count += 1

        # 「シャドーイング」ボタンを表示するために再描画
        st.rerun()    # モード：「シャドーイング」

              