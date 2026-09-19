# MyAssistant

MyAssistant is a personal AI computer assistant designed for Windows.

The goal of this project is to build an intelligent assistant that can understand natural-language commands and safely interact with the computer on the user's behalf.

## Current Features

- Local AI using Ollama
- Qwen3 4B language model
- Natural-language command understanding
- Windows application control (allow-list protected)
- Folder opening and management
- File listing and counting
- Safe folder creation (path traversal protected)
- Personal memory
- Persistent conversation memory
- Safety-focused allow-list for computer control
- Offline AI capability

## Planned Features

- Voice input and speech recognition
- Voice responses
- Faster natural-language understanding
- Advanced computer control (clicking, typing, shortcuts)
- Online and offline AI modes
- Long-term SQLite personal memory
- Screen understanding
- Web access and sandboxed tools
- Multi-step autonomous tasks with verification
- User authentication
- Multi-tier permission and confirmation system
- Desktop graphical interface (tray app)
- Error handling and recovery

## Architecture

```text
User
  ↓
Voice / Text Input
  ↓
AI Intent Understanding (Ollama / Qwen3 4B)
  ↓
Safety & Permission Layer (Deterministic Python Allow-Lists)
  ↓
Computer Tools
  ↓
Windows OS
```

## Prerequisites & Installation

1. **Python 3.10+ (64-bit)** (Tested on Python 3.13)
2. **Ollama Installed and Running:**
   ```bash
   ollama pull qwen3:4b
   ollama serve
   ```
3. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Assistant

```bash
python main.py
```

## Running Automated Tests

A comprehensive unit and regression test suite verifies safety boundaries, allow-lists, and path traversal prevention:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Phase 1 Hardening & Recent Improvements

- **Ollama Schema Synchronization:** Added `move_mouse` and `help` to the JSON schema enum, preventing token hallucination loops.
- **Windows Explorer Protection:** Restricted termination of `explorer.exe` to prevent Windows desktop shell crashes.
- **Path Traversal Protection:** Hardened `create_folder` with strict `pathlib.Path` resolution and filename sanitization against invalid characters (`<>:"/\\|?*`).
- **Startup Fault Tolerance:** Wrapped Ollama warmup in protective exception handling to prevent startup crashes when Ollama is offline.
- **Code Cleanliness:** Removed redundant duplicate routing blocks.
- **Dependency & Test Management:** Added `requirements.txt` and automated test suite in `tests/`.
