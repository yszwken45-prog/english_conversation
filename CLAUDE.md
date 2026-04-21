# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run main.py
```

Requires a `.env` file with:
```
OPENAI_API_KEY=sk-...
```

## Architecture

This is a Streamlit-based English conversation practice app. All application logic runs in a single `main.py` that Streamlit re-executes on every user interaction.

**Entry points and data flow:**
- `main.py` — top-level UI and control flow. Handles login gate, sidebar, mode selection, and dispatches to mode-specific logic within the same file.
- `functions.py` — stateful helpers that read/write `st.session_state` directly (audio recording, transcription, chain creation, TTS).
- `constants.py` — all LLM system prompts and UI option lists.
- `database.py` — SQLite persistence (`app_data.db`). Tables: `users`, `conversation_history`.
- `auth.py` — PBKDF2 password hashing and credential verification against the DB.

**Session state lifecycle:**
- `"logged_in"` / `"user_id"` / `"username"` are initialized once at module load (outside the `if "messages" not in st.session_state` guard).
- All other state (messages, flags, LLM objects, chains) is initialized inside `if "messages" not in st.session_state`, which runs once per login session. On login, today's messages are loaded from the DB into `st.session_state.messages`.
- Logout deletes all session_state keys and calls `st.rerun()`.

**Saving messages:** Use `_append_and_save(role, content)` (defined in `main.py`) instead of appending directly to `st.session_state.messages`. This writes to both the in-memory list and the SQLite DB.

**Three learning modes** (selected via dropdown, all in `main.py`):
- `MODE_1` 日常英会話 — voice in → Whisper transcription → GPT-4o-mini via `ConversationChain` → TTS out. Uses `chain_basic_conversation` with persistent `ConversationSummaryBufferMemory`.
- `MODE_2` シャドーイング — AI generates a sentence (TTS), user repeats by voice, Whisper transcribes, GPT evaluates similarity.
- `MODE_3` ディクテーション — same as shadowing but user types the answer via `st.chat_input` instead of speaking.

**LangChain version is pinned to 0.1.x** (`langchain==0.1.20`). Do not upgrade without testing — the `ConversationChain` / `ConversationSummaryBufferMemory` API changed significantly in later versions.

## Key Constraints

- `audio/input/` and `audio/output/` directories must exist; audio files are created at runtime with timestamp-based names and deleted after use.
- `app_data.db` is gitignored and created automatically on first run by `database.init_db()`.
- The `streamlit-audiorecorder` and `audio-recorder-streamlit` packages both appear in requirements — `audiorecorder` from `streamlit-audiorecorder==0.0.6` is the one actually imported in `functions.py`.
