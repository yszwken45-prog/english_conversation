import streamlit as st
import os
import time
from pathlib import Path
import wave
from pydub import AudioSegment
from audiorecorder import audiorecorder
import numpy as np
from scipy.io.wavfile import write
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
import constants as ct
import re

def record_audio(audio_input_file_path):
    """
    音声入力を受け取って音声ファイルを作成
    """

    audio = audiorecorder(
        start_prompt="発話開始",
        pause_prompt="やり直す",
        stop_prompt="発話終了",
        start_style={"color":"white", "background-color":"black"},
        pause_style={"color":"gray", "background-color":"white"},
        stop_style={"color":"white", "background-color":"black"}
    )

    if len(audio) > 0:
        audio.export(audio_input_file_path, format="wav")
    else:
        st.stop()

def transcribe_audio(audio_input_file_path):
    """
    音声入力ファイルから文字起こしテキストを取得
    Args:
        audio_input_file_path: 音声入力ファイルのパス
    """

    with open(audio_input_file_path, 'rb') as audio_input_file:
        transcript = st.session_state.openai_obj.audio.transcriptions.create(
            model="whisper-1",
            file=audio_input_file,
            language="en"
        )
    
    # 音声入力ファイルを削除
    os.remove(audio_input_file_path)

    return transcript

def save_to_wav(llm_response_audio, audio_output_file_path):
    """
    一旦mp3形式で音声ファイル作成後、wav形式に変換
    Args:
        llm_response_audio: LLMからの回答の音声データ
        audio_output_file_path: 出力先のファイルパス
    """

    temp_audio_output_filename = f"{ct.AUDIO_OUTPUT_DIR}/temp_audio_output_{int(time.time())}.mp3"
    with open(temp_audio_output_filename, "wb") as temp_audio_output_file:
        temp_audio_output_file.write(llm_response_audio)
    
    audio_mp3 = AudioSegment.from_file(temp_audio_output_filename, format="mp3")
    audio_mp3.export(audio_output_file_path, format="wav")

    # 音声出力用に一時的に作ったmp3ファイルを削除
    os.remove(temp_audio_output_filename)

def play_wav(audio_output_file_path, speed=1.0):
    """
    音声ファイルの読み上げ
    Args:
        audio_output_file_path: 音声ファイルのパス
        speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
    """

    # 音声ファイルの読み込み
    audio = AudioSegment.from_wav(audio_output_file_path)

    # 速度を変更
    if speed != 1.0:
        # frame_rateを変更することで速度を調整
        modified_audio = audio._spawn(
            audio.raw_data, 
            overrides={"frame_rate": int(audio.frame_rate * speed)}
        )
        # 元のframe_rateに戻すことで正常再生させる（ピッチを保持したまま速度だけ変更）
        modified_audio = modified_audio.set_frame_rate(audio.frame_rate)

        modified_audio.export(audio_output_file_path, format="wav")

    # Streamlitのst.audioを使用して再生
    with open(audio_output_file_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        st.audio(audio_bytes, format="audio/wav")

    # LLMからの回答の音声ファイルを削除
    os.remove(audio_output_file_path)

def create_chain(system_template):
    """
    LLMによる回答生成用のChain作成
    """

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_template),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}")
    ])
    chain = ConversationChain(
        llm=st.session_state.llm,
        memory=st.session_state.memory,
        prompt=prompt
    )

    return chain

# def create_problem_and_play_audio():
    
#     """
#     問題生成と音声ファイルの再生
#     Args:
#         chain: 問題文生成用のChain
#         speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
#         openai_obj: OpenAIのオブジェクト
#     """

#     # 問題文を生成するChainを実行し、問題文を取得
#     try:
#         problem = st.session_state.chain_create_problem.predict(input="")

#     # LLMからの回答を音声データに変換
#         llm_response_audio = st.session_state.openai_obj.audio.speech.create(
#             model="tts-1",
#             voice="alloy",
#             input=problem
#         )

#     # 音声ファイルの作成
#         audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
#         save_to_wav(llm_response_audio.content, audio_output_file_path)

#     # 音声ファイルの読み上げ
#         play_wav(audio_output_file_path, st.session_state.speed)

#         return problem, audio_output_file_path
#     except Exception as e:
#         print(f"Error: {e}")
#         # ここで return し忘れると、関数は None を返す
#         # 代入時に TypeError: cannot unpack non-iterable NoneType object が発生
#         return None, None  # 回避策：ダミーの値を返す
def create_problem_and_play_audio():
    try:
        # 1. 問題生成
        problem = st.session_state.chain_create_problem.predict(input="")

        # 2. 音声データ生成
        llm_response_audio = st.session_state.openai_obj.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=problem
        )

        # 3. 保存先を一時フォルダに（安全策）
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            audio_output_file_path = fp.name
            
        # 保存実行
        save_to_wav(llm_response_audio.content, audio_output_file_path)

        # --- 重要：サーバー上での直接再生は絶対にエラーになるので消すかコメントアウト ---
        # play_wav(audio_output_file_path, st.session_state.speed)

        return problem, audio_output_file_path

    except Exception as e:
        # コンソールだけでなく画面にもエラーを出して原因を特定する
        st.error(f"関数内でエラーが発生しました: {e}")
        # None, None ではなく、最低限の「文字列」と「空文字」を返す
        return "問題を作成できませんでした。", ""



def get_audio_bytes(audio_output_file_path):
    """ファイルからバイナリデータを取得する"""
    try:
        with open(audio_output_file_path, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        return None

def create_evaluation():
    """
    ユーザー入力値の評価生成
    """

    llm_response_evaluation = st.session_state.chain_evaluation.predict(input="")

    return llm_response_evaluation




def normalize_text(text):
    """
    比較用テキストのクリーニング
    1. 小文字化
    2. 文末の記号 (.?!) を削除
    3. 前後の余計な空白を削除
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[.\?\!]', '', text) # 記号の削除
    return text.strip()

def check_answer(user_input, correct_answer):
    """
    正規化されたテキストで正誤判定を行う
    """
    norm_user = normalize_text(user_input)
    norm_correct = normalize_text(correct_answer)
    
    if norm_user == norm_correct:
        return True, "Perfect! 正解です！"
    else:
        # どのくらい合っているかなどのフィードバックをここに追加可能
        return False, f"惜しい！ 正解は: {correct_answer}"
    
def get_audio_data(response_content):
    """
    HttpxBinaryResponseContent から直接バイトデータを取り出す
    """
    # response_content が HttpxBinaryResponseContent の場合、.content で取得可能
    if hasattr(response_content, "content"):
        return response_content.content
    return response_content



def play_wav(audio_output_file_path, speed):
    # 1. フォルダが存在するか確認し、なければ作成する
    dir_name = os.path.dirname(audio_output_file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    # 2. ファイルの読み込みと再生
    try:
        if os.path.exists(audio_output_file_path):
            with open(audio_output_file_path, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/wav", autoplay=True)
        else:
            st.error(f"ファイルが見つかりません: {audio_output_file_path}")
    except Exception as e:
        st.error(f"再生エラー: {e}")


# functions.py

def create_problem_and_play_audio():
    # session_state に chain があるか確認
    if "chain_create_problem" not in st.session_state:
        # もし未初期化なら、ここで初期化関数を呼ぶなどして回避する
        st.error("AIの初期化に失敗しました。ページをリロードしてください。")
        return None, None

    # 安全に呼び出し
    problem = st.session_state.chain_create_problem.predict(input="")
    # ... 以下の処理 ...