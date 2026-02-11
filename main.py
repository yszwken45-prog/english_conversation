import streamlit as st
import os
import time
from time import sleep
from pathlib import Path
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
import functions as ft
import constants as ct


# 各種設定
load_dotenv()
st.set_page_config(
    page_title=ct.APP_NAME
)

# タイトル表示
st.markdown(f"## {ct.APP_NAME}")

# 初期処理
if "messages" not in st.session_state:
    st.session_state.messages = []
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
    # main.py の初期化セクションに追加
    if "problem" not in st.session_state:
        st.session_state.problem = ""
    if "audio_path" not in st.session_state:
        st.session_state.audio_path = None

    
    st.session_state.openai_obj = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    st.session_state.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
    st.session_state.memory = ConversationSummaryBufferMemory(
        llm=st.session_state.llm,
        max_token_limit=1000,
        return_messages=True
    )

    # モード「日常英会話」用のChain作成
    st.session_state.chain_basic_conversation = ft.create_chain(ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION)

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
    st.session_state.englv = st.selectbox(label="英語レベル", options=ct.ENGLISH_LEVEL_OPTION, label_visibility="collapsed")

# オーディオ再生のためのプレースホルダーを定義
if "audio_placeholder" not in st.session_state:
    st.session_state.audio_placeholder = st.empty()

audio_placeholder = st.session_state.audio_placeholder

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
# main.py の上部、あるいは実行ボタンの直前
if "chain_create_problem" not in st.session_state:
    # ここで LangChain の初期化を行う関数を呼ぶ
    # 例: st.session_state.chain_create_problem = ft.initialize_chain()
    st.session_state.chain_create_problem = ft.create_chain(ct.SYSTEM_TEMPLATE_CREATE_PROBLEM)
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
    if st.session_state.mode == ct.MODE_3 and (st.session_state.dictation_button_flg or st.session_state.dictation_count == 0 or st.session_state.dictation_chat_message):
        if st.session_state.dictation_first_flg:
            st.session_state.chain_create_problem = ft.create_chain(ct.SYSTEM_TEMPLATE_CREATE_PROBLEM)
            st.session_state.dictation_first_flg = False
        # チャット入力以外
        if not st.session_state.chat_open_flg:
            with st.spinner('問題文生成中...'):
                problem, audio_path = ft.create_problem_and_play_audio()

                if problem is None or audio_path is None:
                    st.error("問題の生成または音声ファイルの作成に失敗しました。再試行してください。")
                    st.stop()

                st.session_state.problem = problem
                st.session_state.audio_path = audio_path

            st.session_state.chat_open_flg = True
            st.session_state.dictation_flg = False
            st.rerun()
        # チャット入力時の処理
        else:
            if not st.session_state.dictation_chat_message:
                st.stop()

            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(st.session_state.problem)
            with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                st.markdown(st.session_state.dictation_chat_message)

            st.session_state.messages.append({"role": "assistant", "content": st.session_state.problem})
            st.session_state.messages.append({"role": "user", "content": st.session_state.dictation_chat_message})

            with st.spinner('評価結果の生成中...'):
                system_template = ct.SYSTEM_TEMPLATE_EVALUATION.format(
                    llm_text=st.session_state.problem,
                    user_text=st.session_state.dictation_chat_message
                )
                st.session_state.chain_evaluation = ft.create_chain(system_template)
                llm_response_evaluation = ft.create_evaluation()

            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(llm_response_evaluation)
            st.session_state.messages.append({"role": "assistant", "content": llm_response_evaluation})
            st.session_state.messages.append({"role": "other"})

            st.session_state.dictation_flg = True
            st.session_state.dictation_chat_message = ""
            st.session_state.dictation_count += 1
            st.session_state.chat_open_flg = False

            st.rerun()

# オーディオ再生のエラーハンドリング
if st.session_state.audio_path:
    try:
        audio_placeholder.audio(ft.get_audio_bytes(st.session_state.audio_path), format="audio/wav")
    except Exception as e:
        st.error(f"音声ファイルの再生中にエラーが発生しました: {e}")