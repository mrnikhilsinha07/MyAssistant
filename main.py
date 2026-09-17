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
# Allowed applications for closing
CLOSE_APPS = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "explorer": "explorer.exe"
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
def close_application(app_name):
    app_name = app_name.strip().lower()

    if app_name not in CLOSE_APPS:
        print(f"Assistant: I am not allowed to close '{app_name}'.")
        return

    process_name = CLOSE_APPS[app_name]

    try:
        subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True
        )
        print(f"Assistant: Closed {app_name}.")
    except Exception as error:
        print(f"Assistant: I could not close {app_name}.")
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

    elif action_type == "close_app":
        close_application(target)    

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
You are the command interpreter for a personal Windows AI assistant.

Your job is to understand the user's NATURAL LANGUAGE and convert their request into exactly ONE safe JSON action.

The user can phrase the same request in any way. Do NOT depend on exact phrases or keywords.

Return VALID JSON ONLY. Never return explanations, markdown, or extra text.

ALLOWED ACTIONS:

1. OPEN APPLICATION
Use when the user wants to launch an application.

JSON:
{"action":"open_app","target":"chrome"}

Allowed applications:
- chrome
- notepad
- calculator
- explorer

Examples:
"open calculator"
"can you launch the calculator?"
"I need the calculator"
"start Chrome"
"please open Notepad"

All of these mean open_app.

2. CLOSE APPLICATION
Use when the user wants to close an allowed application.

JSON:
{"action":"close_app","target":"calculator"}

Allowed applications:
- chrome
- notepad
- calculator
- explorer

Examples:
"close calculator"
"can you close Chrome?"
"shut down Notepad"
"please exit the calculator"

All of these mean close_app.

3. OPEN FOLDER
Use when the user wants to open a Windows folder.

JSON:
{"action":"open_folder","target":"downloads"}

Allowed folders:
- downloads
- documents
- desktop
- pictures
- videos
- music

Examples:
"open Downloads"
"take me to my Downloads folder"
"can you open my Downloads?"
"I want to see my Downloads folder"

These mean open_folder.

4. LIST FILES
Use when the user wants to SEE, SHOW, LIST, CHECK, or KNOW WHAT FILES are inside an allowed folder.

JSON:
{"action":"list_files","target":"downloads"}

Examples:
"show me what files are in Downloads"
"what files do I have in Downloads?"
"list my Downloads"
"tell me what's inside my Downloads folder"
"check my Downloads"
"show the contents of Downloads"

These mean list_files, NOT open_folder.

IMPORTANT:
If the user asks what files are inside a folder, use list_files.
If the user asks to open or go to a folder, use open_folder.

5. CREATE FOLDER
Use when the user wants to create a new folder.

JSON:
{"action":"create_folder","target":"MyFolder"}

Only create folders inside the allowed Documents location.

6. HELP
JSON:
{"action":"help","target":""}

7. SAVE PERSONAL MEMORY
Use ONLY when the user explicitly asks you to remember something.

JSON:
{"action":"remember","target":"favorite_game","value":"Valorant"}

Never invent personal information.

8. RETRIEVE PERSONAL MEMORY
Use when the user asks about something that may have been saved in personal memory.

JSON:
{"action":"recall","target":"favorite_game"}

9. NORMAL CONVERSATION
For questions, explanations, casual conversation, or requests that cannot safely be performed.

JSON:
{"action":"chat","target":"","response":"your response"}

INTENT RULES:

- Understand the meaning of the entire sentence, not just individual words.
- Do not require exact wording.
- Different natural-language phrases with the same meaning must produce the same action.
- Never guess an application, folder, file path, or personal fact.
- If the request is ambiguous, unsafe, or unsupported, use chat.
- Never execute shell commands or PowerShell commands.
- Never invent applications.
- Never invent folders.
- Never access arbitrary file paths.
- Never execute anything outside the allowed actions.
- Never perform destructive actions.
- Never delete, modify, move, upload, download, install, or uninstall anything unless a future tool explicitly allows it.
- Only use the allowed folders and applications listed above.

MOST IMPORTANT DISTINCTION:

"Open my Downloads folder"
=> {"action":"open_folder","target":"downloads"}

"Show me the files in my Downloads folder"
=> {"action":"list_files","target":"downloads"}

"What's inside my Downloads?"
=> {"action":"list_files","target":"downloads"}

"Take me to Downloads"
=> {"action":"open_folder","target":"downloads"}

Always choose the action based on the user's INTENT.
"""
    try:
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Do not include previous conversation when interpreting a new computer command.

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
        print("AI ACTION:", action)

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