# MyAssistant

MyAssistant is a personal AI computer assistant designed for Windows.

The goal of this project is to create a local-first assistant that can understand natural-language commands, interact with the computer, manage files safely, and maintain persistent local memory.

The assistant uses a local AI model through Ollama and is designed to progressively support more advanced computer-control and autonomous capabilities.

## Current Features

- Local AI processing using Ollama
- Qwen3 1.7B language model
- Natural-language command understanding
- Windows application control
- File and folder creation
- Nested folder creation
- File listing and counting
- File reading
- File writing
- Documents-folder protection for file operations
- Path-traversal protection
- Persistent local memory
- Personal memory recall
- Safety-focused deterministic action validation
- Protected computer-control actions
- Offline AI capability
- Clean shutdown with Ctrl+C / EOF handling

## Planned Features

- Voice input and speech recognition
- Voice responses
- Faster natural-language command understanding
- Advanced computer control (clicking, typing, keyboard shortcuts)
- Online and offline operating modes
- Long-term SQLite-based personal memory
- Screen understanding
- Web access and sandboxed tools
- Multi-step autonomous tasks with verification
- User authentication
- Multi-level permission and confirmation system
- Desktop graphical interface
- System tray application
- Error handling and recovery
- Task history and execution logs

## Architecture

```text
User
  ↓
Voice / Text Input
  ↓
AI Intent Understanding
(Ollama / Qwen3 1.7B)
  ↓
Action Planning
  ↓
Safety & Permission Layer
(Deterministic Python Validation)
  ↓
Computer / File / Memory Tools
  ↓
Windows OS