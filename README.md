# MyAssistant

MyAssistant is a personal AI computer assistant designed for Windows.

The goal of this project is to build an intelligent assistant that can understand natural-language commands and safely interact with the computer on the user's behalf.

## Current Features

- Local AI using Ollama
- Qwen3 4B language model
- Natural-language command understanding
- Windows application control
- Folder opening and management
- File listing
- Folder creation
- Personal memory
- Persistent conversation memory
- Safety-focused allow-list for computer control
- Offline AI capability

## Planned Features

- Voice input and speech recognition
- Voice responses
- Faster natural-language understanding
- Advanced computer control
- Online and offline AI modes
- Long-term personal memory
- Screen understanding
- Web access
- Multi-step autonomous tasks
- User authentication
- Permission and confirmation system
- Desktop graphical interface
- Error handling and recovery

## Architecture

```text
User
  ↓
Voice / Text Input
  ↓
AI Intent Understanding
  ↓
Safety & Permission Layer
  ↓
Computer Tools
  ↓
Windows
