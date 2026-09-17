import os
import subprocess
import json
from datetime import datetime
import ollama

# ==========================================
# MY PERSONAL ASSISTANT
# Stage 3: Local AI Brain + Computer Control
# ==========================================

MODEL = "qwen3:4b"

# Personal memory
PERSONAL_MEMORY_FILE = os.path.join(
    os.path.dirname(__file__),
    "personal_memory.json"
)

try:
    with open(PERSONAL_MEMORY_FILE, "r", encoding="utf-8") as file:
        personal_memory = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    personal_memory = {}

# Persistent conversation memory
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        conversation_history = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    conversation_history = []

# Allowed applications
APPS = {
    "chrome": ["cmd", "/c", "start", "", "chrome"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calculator app": ["calc.exe"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
}

# Allowed folders
def get_folders():
    home = os.path.expanduser("~")

    return {
        "downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "desktop": os.path.join(home, "Desktop"),
        "pictures": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "music": os.path.join(home, "Music"),
    }


def open_application(app_name):
    app_name = app_name.strip().lower()

    if app_name not in APPS:
        print(f"Assistant: I am not allowed to open '{app_name}'.")
        return

    try:
        subprocess.Popen(APPS[app_name])
        print(f"Assistant: Opening {app_name}.")
    except Exception as error:
        print(f"Assistant: I could not open {app_name}.")
        print(f"System error: {error}")


def open_folder(folder_name):
    folders = get_folders()
    folder_name = folder_name.strip().lower()

    if folder_name not in folders:
        print(f"Assistant: I don't have permission to open '{folder_name}'.")
        return

    path = folders[folder_name]

    if os.path.exists(path):
        os.startfile(path)
        print(f"Assistant: Opening your {folder_name} folder.")
    else:
        print(f"Assistant: I could not find your {folder_name} folder.")


def list_files(folder_name):
    folders = get_folders()
    folder_name = folder_name.strip().lower()

    if folder_name not in folders:
        print(f"Assistant: I don't have access to '{folder_name}'.")
        return

    path = folders[folder_name]

    if not os.path.exists(path):
        print(f"Assistant: I could not find your {folder_name} folder.")
        return

    items = os.listdir(path)

    print(f"\nAssistant: Contents of {folder_name}:")

    if not items:
        print("  The folder is empty.")
    else:
        for item in items:
            print(f"  - {item}")

    print()


def create_folder(folder_name):
    folder_name = folder_name.strip()

    if not folder_name:
        print("Assistant: Please provide a folder name.")
        return

    safe_location = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        folder_name
    )

    if os.path.exists(safe_location):
        print("Assistant: That folder already exists.")
        return

    try:
        os.makedirs(safe_location)
        print(
            f"Assistant: Created '{folder_name}' "
            "inside your Documents folder."
        )
    except Exception as error:
        print("Assistant: I could not create the folder.")
        print(f"System error: {error}")


def show_help():
    print()
    print("Assistant: Available commands:")
    print("  hello")
    print("  time")
    print("  open chrome")
    print("  open notepad")
    print("  open calculator")
    print("  open explorer")
    print("  open downloads")
    print("  open documents")
    print("  open desktop")
    print("  list downloads")
    print("  list documents")
    print("  list desktop")
    print("  create folder <name>")
    print("  help")
    print("  exit")
    print()


def execute_action(action):
    action_type = action.get("action", "")
    target = action.get("target", "")

    if action_type == "open_app":
        open_application(target)

    elif action_type == "open_folder":
        open_folder(target)

    elif action_type == "list_files":
        list_files(target)

    elif action_type == "create_folder":
        create_folder(target)

    elif action_type == "time":
        current_time = datetime.now().strftime("%I:%M %p")
        print(f"Assistant: The current time is {current_time}.")

    elif action_type == "help":
        show_help()

    elif action_type == "remember":
        save_personal_memory(target, action.get("value", ""))

    elif action_type == "recall":
        value = get_personal_memory(target)

        if value:
            print(f"Assistant: Your {target} is {value}.")
        else:
            print(f"Assistant: I don't have anything saved for {target}.")

    elif action_type == "chat":
        print(f"Assistant: {action.get('response', 'I am ready.')}")

    else:
        print("Assistant: I could not determine a safe action.")
def save_personal_memory(key, value):
    personal_memory[key] = value

    with open(PERSONAL_MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(personal_memory, file, indent=2)

    print(f"Assistant: I will remember that your {key} is {value}.")


def get_personal_memory(key):
    return personal_memory.get(key)
def ask_local_ai(user_message):
    system_prompt = """
You are the command interpreter for a personal Windows assistant.

Return valid JSON only.

Allowed actions:

1. Open an application:
{"action":"open_app","target":"chrome"}

Allowed apps:
chrome, notepad, calculator, file explorer, explorer

2. Open a folder:
{"action":"open_folder","target":"downloads"}

Allowed folders:
downloads, documents, desktop, pictures, videos, music

3. List files:
{"action":"list_files","target":"downloads"}

4. Create a folder:
{"action":"create_folder","target":"MyFolder"}

5. Show help:
{"action":"help","target":""}

6. Save personal memory:
{"action":"remember","target":"favorite_game","value":"Valorant"}

7. Retrieve personal memory:
{"action":"recall","target":"favorite_game"}

8. Normal conversation:
{"action":"chat","target":"","response":"your response"}

Memory rules:
- Use "remember" when the user explicitly asks you to remember a personal fact.
- Use "recall" when the user asks about something that may be stored in personal memory.
- Only store information explicitly provided by the user.
- Never invent personal information.

IMPORTANT SECURITY RULES:
- Never invent applications.
- Never invent folders.
- Never provide shell commands.
- Never provide PowerShell commands.
- Never request arbitrary file paths.
- Never execute anything outside the allowed actions.
- If a request is unsafe or unsupported, use chat and explain briefly.
"""

    try:
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        messages.extend(conversation_history)

        messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        response = ollama.chat(
            model=MODEL,
            messages=messages,
            format="json",
            think=False
        )
        content = response["message"]["content"]
        action = json.loads(content)

        execute_action(action)
        conversation_history.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        if len(conversation_history) > 10:
            conversation_history.pop(0)

        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(conversation_history, file, indent=2)       
                

    except Exception as error:
        print("Assistant: I could not contact my local AI.")
        print(f"System error: {error}")
def process_command(command):
    command = command.strip()

    if command == "":
        return

    command_lower = command.lower()

    # Exit
    if command_lower == "exit":
        print("Assistant: Shutting down. Goodbye.")
        return "exit"

    # Basic direct commands
    if command_lower == "hello":
        print("Assistant: Hello. I am ready.")
        return

    if command_lower == "time":
        current_time = datetime.now().strftime("%I:%M %p")
        print(f"Assistant: The current time is {current_time}.")
        return

    if command_lower == "help":
        show_help()
        return
        # Reliable personal memory recall
    if command_lower.startswith("what is my "):
        memory_key = command_lower[11:].strip(" ?.!").replace(" ", "_")

        if memory_key in personal_memory:
            print(f"Assistant: Your {memory_key.replace('_', ' ')} is {personal_memory[memory_key]}.")
        else:
            print(f"Assistant: I don't have anything saved for {memory_key.replace('_', ' ')}.")
        return

    if command_lower.startswith("what's my "):
        memory_key = command_lower[10:].strip(" ?.!").replace(" ", "_")

        if memory_key in personal_memory:
            print(f"Assistant: Your {memory_key.replace('_', ' ')} is {personal_memory[memory_key]}.")
        else:
            print(f"Assistant: I don't have anything saved for {memory_key.replace('_', ' ')}.")
        return
        # Reliable file listing commands
    if command_lower == "list downloads":
        execute_action({
            "action": "list_files",
            "target": "downloads"
        })
        return

    if command_lower == "list documents":
        execute_action({
            "action": "list_files",
            "target": "documents"
        })
        return

    if command_lower == "list desktop":
        execute_action({
            "action": "list_files",
            "target": "desktop"
        })
        return

    if command_lower == "list pictures":
        execute_action({
            "action": "list_files",
            "target": "pictures"
        })
        return

    if command_lower == "list videos":
        execute_action({
            "action": "list_files",
            "target": "videos"
        })
        return

    if command_lower == "list music":
        execute_action({
            "action": "list_files",
            "target": "music"
        })
        return    # Reliable file listing commands
    if command_lower == "list downloads":
        execute_action({
            "action": "list_files",
            "target": "downloads"
        })
        return

    if command_lower == "list documents":
        execute_action({
            "action": "list_files",
            "target": "documents"
        })
        return

    if command_lower == "list desktop":
        execute_action({
            "action": "list_files",
            "target": "desktop"
        })
        return

    if command_lower == "list pictures":
        execute_action({
            "action": "list_files",
            "target": "pictures"
        })
        return

    if command_lower == "list videos":
        execute_action({
            "action": "list_files",
            "target": "videos"
        })
        return

    if command_lower == "list music":
        execute_action({
            "action": "list_files",
            "target": "music"
        })
        return
        # Reliable direct commands
    direct_apps = {
        "calculator": "calculator",
        "notepad": "notepad",
        "chrome": "chrome",
        "file explorer": "explorer",
        "explorer": "explorer"
    }

    direct_folders = {
        "downloads": "downloads",
        "documents": "documents",
        "desktop": "desktop",
        "pictures": "pictures",
        "videos": "videos",
        "music": "music"
    }

    if command_lower.startswith("open "):
        target = command_lower[5:].strip()

        if target in direct_apps:
            execute_action({
                "action": "open_app",
                "target": direct_apps[target]
            })
            return

        if target in direct_folders:
            execute_action({
                "action": "open_folder",
                "target": direct_folders[target]
            })
            return

    
         # Natural-language app commands
    natural_app_commands = {
        "calculator": "calculator",
        "notepad": "notepad",
        "chrome": "chrome",
        "file explorer": "explorer",
        "explorer": "explorer"
    }

    if command_lower.startswith("can you open "):
        requested_app = command_lower[len("can you open "):].strip()

        for app_name, app_target in natural_app_commands.items():
            if app_name in requested_app:
                execute_action({
                    "action": "open_app",
                    "target": app_target
                })
                return

    if command_lower.startswith("please open "):
        requested_app = command_lower[len("please open "):].strip()

        for app_name, app_target in natural_app_commands.items():
            if app_name in requested_app:
                execute_action({
                    "action": "open_app",
                    "target": app_target
                })
                return

        # Natural-language folder commands
    if "downloads" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "downloads"
        })
        return

    if "documents" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "documents"
        })
        return

    if "desktop" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "desktop"
        })
        return

    if "pictures" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "pictures"
        })
        return

    if "videos" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "videos"
        })
        return

    if "music" in command_lower and ("open" in command_lower):
        execute_action({
            "action": "open_folder",
            "target": "music"
        })
        return
    # Let local AI understand everything else
    ask_local_ai(command)

def main():
    print("========================================")
    print("        MY PERSONAL ASSISTANT")
    print("========================================")
    print("Assistant is online.")
    print("Local AI: ENABLED")
    print("Computer control: ENABLED")
    print("File control: ENABLED")
    print("AI model: qwen3:4b")
    print()
    print("Type 'help' to see commands.")
    print("Type 'exit' to shut down.")
    print()

    while True:
        command = input("You: ")

        result = process_command(command)

        if result == "exit":
            break


if __name__ == "__main__":
    main()