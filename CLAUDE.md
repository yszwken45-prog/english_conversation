# CLAUDE.md

このファイルは、リポジトリのコードを扱う際に Claude Code (claude.ai/code) へ提供するガイダンスです。

## アプリの起動

```bash
streamlit run main.py
```

以下の内容を含む `.env` ファイルが必要です:
```
OPENAI_API_KEY=sk-...
```

## アーキテクチャ

Streamlit ベースの英会話練習アプリです。すべてのアプリケーションロジックは単一の `main.py` 内で動作し、ユーザー操作のたびに Streamlit が再実行します。

**エントリーポイントとデータフロー:**
- `main.py` — トップレベルの UI と制御フロー。ログインゲート、サイドバー、モード選択を処理し、同ファイル内のモード別ロジックに処理を振り分ける。
- `functions.py` — `st.session_state` を直接読み書きするステートフルなヘルパー群（音声録音・文字起こし・チェーン生成・TTS）。
- `constants.py` — LLM のシステムプロンプトおよび UI 選択肢リストをすべて定義。
- `database.py` — SQLite 永続化（`app_data.db`）。テーブル: `users`, `conversation_history`。
- `auth.py` — PBKDF2 によるパスワードハッシュ化と DB を用いた認証。

**セッションステートのライフサイクル:**
- `"logged_in"` / `"user_id"` / `"username"` はモジュールロード時に一度だけ初期化される（`if "messages" not in st.session_state` ガードの外）。
- その他すべてのステート（messages・フラグ・LLM オブジェクト・チェーン）は `if "messages" not in st.session_state` 内で初期化され、ログインセッションごとに一度だけ実行される。ログイン時に当日のメッセージが DB から `st.session_state.messages` に読み込まれる。
- ログアウト時はすべての session_state キーを削除し、`st.rerun()` を呼び出す。

**メッセージの保存:** `st.session_state.messages` に直接追記せず、`_append_and_save(role, content)`（`main.py` 内で定義）を使うこと。これにより、インメモリリストと SQLite DB の両方に書き込まれる。

**3 つの学習モード**（ドロップダウンで選択、すべて `main.py` 内）:
- `MODE_1` 日常英会話 — 音声入力 → Whisper 文字起こし → `ConversationChain` 経由で GPT-4o-mini → TTS 出力。永続化された `ConversationSummaryBufferMemory` を持つ `chain_basic_conversation` を使用。
- `MODE_2` シャドーイング — AI が文章を生成（TTS）、ユーザーが音声で復唱、Whisper が文字起こし、GPT が類似度を評価。
- `MODE_3` ディクテーション — シャドーイングと同様だが、ユーザーは音声ではなく `st.chat_input` でテキスト入力する。

**LangChain のバージョンは 0.1.x に固定**（`langchain==0.1.20`）。`ConversationChain` / `ConversationSummaryBufferMemory` の API は後続バージョンで大きく変更されているため、テストなしにアップグレードしないこと。

## 重要な制約

- `audio/input/` および `audio/output/` ディレクトリが存在している必要がある。音声ファイルは実行時にタイムスタンプ付きのファイル名で作成され、使用後に削除される。
- `app_data.db` は .gitignore に含まれており、初回起動時に `database.init_db()` によって自動生成される。
- `streamlit-audiorecorder` と `audio-recorder-streamlit` の両パッケージが requirements に記載されているが、`functions.py` で実際にインポートされるのは `streamlit-audiorecorder==0.0.6` の `audiorecorder` のみ。
