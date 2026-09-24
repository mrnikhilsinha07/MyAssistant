import os
import subprocess
import json
import time
import re
from datetime import datetime
from pathlib import Path
import ollama
import pyautogui
import memory_manager
from ddgs import DDGS
import ctypes


def web_search(query, num_results=5):
    """Search the web using DDGS."""
    try:
        results = DDGS().text(
            query,
            max_results=num_results
        )

        formatted_results = []

        for result in results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", "")
            })

        return formatted_results

    except Exception as e:
        print(f"Web search error: {e}")
        return [{"error": str(e)}]
# ==========================================
# MY PERSONAL ASSISTANT
# Stage 3: Local AI Brain + Computer Control
# ==========================================

MODEL = "qwen3:1.7b"
def summarize_search_results(query, results):
    """Summarize web search results using the local AI."""
    try:
        sources = []

        for item in results[:5]:
            sources.append(
                f"Title: {item.get('title', '')}\n"
                f"Snippet: {item.get('snippet', '')}\n"
                f"URL: {item.get('url', '')}"
            )

        prompt = f"""
Summarize the following web search results for the user.

User query:
{query}

Search results:
{chr(10).join(sources)}

Rules:
- Give a concise factual summary.
- Use only information contained in the provided search results.
- Do not invent facts.
- Mention important differences or uncertainty when present.
- Do not include unnecessary filler.
"""

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            think=False
        )

        return response["message"]["content"].strip()

    except Exception as e:
        print(f"Web summary error: {e}")
        return ""
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
    "calculator app": "CalculatorApp.exe",
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


def move_mouse(x, y):
    try:
        x = int(x)
        y = int(y)

        screen_width, screen_height = pyautogui.size()

        if not (0 <= x < screen_width and 0 <= y < screen_height):
            print("Assistant: Mouse position is outside the screen.")
            return False

        pyautogui.moveTo(x, y, duration=0.2)
        print(f"Assistant: Moved mouse to ({x}, {y}).")
        return True

    except Exception as e:
        print(f"Assistant: Could not move mouse: {e}")
        return False
    
def open_application(app_name):
    app_name = app_name.strip().lower()

    if app_name not in APPS:
        print(f"Assistant: I am not allowed to open '{app_name}'.")
        return False

    try:
        process = subprocess.Popen(APPS[app_name])

        time.sleep(0.5)

        if app_name == "notepad":
            ctypes.windll.user32.SetForegroundWindow(process.pid)

        print(f"Assistant: Opening {app_name}.")
        return True
    except Exception as error:
        print(f"Assistant: I could not open {app_name}.")
        print(f"System error: {error}")
        return False

def close_application(app_name):
    app_name = app_name.strip().lower()

    if app_name in {"explorer", "file explorer"}:
        print("Assistant: Closing the Windows Explorer shell is restricted for system safety.")
        return False

    if app_name not in CLOSE_APPS:
        print(f"Assistant: I am not allowed to close '{app_name}'.")
        return False

    process_name = CLOSE_APPS[app_name]

    try:
        if app_name in {"calculator", "calculator app"}:
            subprocess.run(["taskkill", "/IM", "CalculatorApp.exe", "/F"], capture_output=True, text=True)
            subprocess.run(["taskkill", "/IM", "Calculator.exe", "/F"], capture_output=True, text=True)
            subprocess.run(["taskkill", "/IM", "calc.exe", "/F"], capture_output=True, text=True)
        else:
            subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                capture_output=True,
                text=True
            )
        print(f"Assistant: Closed {app_name}.")
        return True
    except Exception as error:
        print(f"Assistant: I could not close {app_name}.")
        print(f"System error: {error}")
        return False

def open_folder(folder_name):
    folders = get_folders()
    folder_name = folder_name.strip().lower()

    if folder_name not in folders:
        print(f"Assistant: I don't have permission to open '{folder_name}'.")
        return False

    path = folders[folder_name]

    if os.path.exists(path):
        os.startfile(path)
        print(f"Assistant: Opening your {folder_name} folder.")
        return True
    else:
        print(f"Assistant: I could not find your {folder_name} folder.")
        return False


def list_files(folder_name):
    folders = get_folders()
    folder_name = folder_name.strip().lower()

    if folder_name not in folders:
        print(f"Assistant: I don't have access to '{folder_name}'.")
        return []

    path = folders[folder_name]

    if not os.path.exists(path):
        print(f"Assistant: I could not find your {folder_name} folder.")
        return []

    try:
        items = os.listdir(path)
        print(f"\nAssistant: Contents of {folder_name}:")
        if not items:
            print("  The folder is empty.")
        else:
            for item in items:
                print(f"  - {item}")
        print()
        return items
    except Exception as e:
        print(f"Assistant: Could not read {folder_name}: {e}")
        return []


def count_files(folder_name):
    folders = get_folders()
    folder_name = folder_name.strip().lower()

    if folder_name not in folders:
        print("Assistant: I can only count files in approved folders.")
        return 0

    path = folders[folder_name]

    if not os.path.exists(path):
        print(f"Assistant: I could not find your {folder_name} folder.")
        return 0

    try:
        files = [
            name for name in os.listdir(path)
            if os.path.isfile(os.path.join(path, name))
        ]
        print(f"Assistant: There are {len(files)} files in your {folder_name.title()} folder.")
        return len(files)
    except Exception as e:
        print(f"Assistant: I could not count the files: {e}")
        return 0


def list_running_applications():
    """List open applications quickly using kernel32 process snapshot (sub-millisecond latency)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260)
        ]

    FRIENDLY_NAMES = {
        "chrome.exe": "Google Chrome",
        "brave.exe": "Brave Browser",
        "msedge.exe": "Microsoft Edge",
        "notepad.exe": "Notepad",
        "calculatorapp.exe": "Calculator",
        "calculator.exe": "Calculator",
        "calc.exe": "Calculator",
        "explorer.exe": "File Explorer",
        "code.exe": "Visual Studio Code",
        "antigravity ide.exe": "Antigravity IDE",
        "spotify.exe": "Spotify",
        "discord.exe": "Discord",
        "whatsapp.root.exe": "WhatsApp",
        "slack.exe": "Slack",
        "teams.exe": "Microsoft Teams",
        "steam.exe": "Steam",
    }

    procs = set()
    hSnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hSnap == -1 or not hSnap:
        print("Assistant: Could not inspect system processes.")
        return []

    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

    if kernel32.Process32First(hSnap, ctypes.byref(pe)):
        while True:
            exe_name = pe.szExeFile.decode("utf-8", "ignore").lower()
            if exe_name in FRIENDLY_NAMES:
                procs.add(FRIENDLY_NAMES[exe_name])
            if not kernel32.Process32Next(hSnap, ctypes.byref(pe)):
                break

    kernel32.CloseHandle(hSnap)
    apps = sorted(procs)

    if apps:
        print("Assistant: Currently open applications:")
        for app in apps:
            print(f" - {app}")
    else:
        print("Assistant: No major user applications are currently detected.")

    return apps


def create_folder(folder_name):
    folder_name = folder_name.strip()

    if not folder_name:
        print("Assistant: Please provide a folder name.")
        return

    # Sanitize invalid Windows filename/directory characters
    if re.search(r'[<>:"/\\|?*]', folder_name):
        print("Assistant: Folder name contains invalid characters.")
        return

    docs_dir = Path(os.path.expanduser("~")) / "Documents"
    target_path = (docs_dir / folder_name).resolve()

    # Ensure target_path stays strictly inside Documents (prevent path traversal)
    try:
        target_path.relative_to(docs_dir.resolve())
    except ValueError:
        print("Assistant: Blocked folder creation outside your Documents folder.")
        return

    if target_path.exists():
        print("Assistant: That folder already exists.")
        return

    try:
        target_path.mkdir(parents=True, exist_ok=False)
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


def validate_action(action):
    """Validate AI-generated actions before they reach computer control."""

    if not isinstance(action, dict):
        print("Assistant: Invalid action format.")
        return False

    # Handle multi-action plans
    if "actions" in action:
        actions = action.get("actions")

        if not isinstance(actions, list) or not actions:
            print("Assistant: Invalid multi-task plan.")
            return False

        for step in actions:
            if not validate_action(step):
                return False

        return True

    action_type = action.get("action", "")
    target = action.get("target", "")

    allowed_actions = {
        "open_app",
        "type_text",
        "press_key",
        "move_mouse",
        "close_app",
        "open_folder",
        "list_files",
        "count_files",
        "list_running_apps",
        "create_folder",
        "time",
        "help",
        "remember",
        "recall",
        "chat",
        "web_search"
    }

    if action_type not in allowed_actions:
        print(f"Assistant: Blocked unknown action '{action_type}'.")
        return False

    # Validate application targets
    if action_type in {"open_app", "close_app"}:
        allowed_apps = {
            "chrome",
            "notepad",
            "calculator",
            "calculator app",
            "explorer",
            "file explorer"
        }

        if target.lower().strip() not in allowed_apps:
            print(f"Assistant: Blocked unknown application '{target}'.")
            return False

    # Validate folder targets
    if action_type in {
        "open_folder",
        "list_files",
        "count_files"
    }:
        allowed_folders = {
            "downloads",
            "documents",
            "desktop",
            "pictures",
            "videos",
            "music"
        }

        if target.lower().strip() not in allowed_folders:
            print(f"Assistant: Blocked unknown folder '{target}'.")
            return False

    return True
def execute_action(action):
    if not validate_action(action):
        return None

    # Handle multiple actions in the exact order requested
    if "actions" in action and isinstance(action["actions"], list):
        results = []

        for step in action["actions"]:
            if isinstance(step, dict):
                result = execute_action(step)
                if result is not None:
                    results.append(str(result))

        return results

    action_type = action.get("action", "")
    target = action.get("target", "")
    res = None

    if action_type == "open_app":
        success = open_application(target)
        res = f"Opened {target}" if success else f"Failed to open {target}"

    elif action_type == "type_text":
        try:
            pyautogui.write(target, interval=0.02)
            print("Assistant: Typed the requested text.")
            res = "Typed the requested text."
        except Exception:
            print("Assistant: Failed to type the requested text.")
            res = "Failed to type the requested text."

    elif action_type == "press_key":
        try:
            pyautogui.press(target)
            print(f"Assistant: Pressed the {target} key.")
            res = f"Pressed the {target} key."
        except Exception:
            print("Assistant: Failed to press the requested key.")
            res = "Failed to press the requested key."
        
    elif action_type == "move_mouse":
        try:
            target_lower = target.strip().lower()

            screen_width, screen_height = pyautogui.size()

            if target_lower == "center":
                x = screen_width // 2
                y = screen_height // 2

            elif target_lower == "top-left":
                x = 0
                y = 0

            elif target_lower == "top-right":
                x = screen_width - 1
                y = 0

            elif target_lower == "bottom-left":
                x = 0
                y = screen_height - 1

            elif target_lower == "bottom-right":
                x = screen_width - 1
                y = screen_height - 1

            else:
                x, y = target.split(",")
                x = int(x.strip())
                y = int(y.strip())

            success = move_mouse(x, y)

            res = (
                f"Moved mouse to ({x}, {y})"
                if success
                else "Failed to move mouse"
            )

        except Exception:
            print("Assistant: Invalid mouse position.")
            res = "Invalid mouse position"
    elif action_type == "close_app":
        success = close_application(target)
        res = f"Closed {target}" if success else f"Failed to close {target}"

    elif action_type == "open_folder":
        success = open_folder(target)
        res = f"Opened {target} folder" if success else f"Failed to open {target}"

    elif action_type == "list_files":
        items = list_files(target)
        res = f"Listed {len(items)} items in {target}"

    elif action_type == "count_files":
        count = count_files(target)
        res = f"Counted {count} files in {target}"

    elif action_type == "list_running_apps":
        apps = list_running_applications()
        res = f"Found {len(apps)} running applications"

    elif action_type == "create_folder":
        folder_name = target.replace("Documents/", "", 1).replace("Documents\\", "", 1)
        create_folder(folder_name)
        res = f"Created folder {target}"

    elif action_type == "time":
        current_time = datetime.now().strftime("%I:%M %p")
        print(f"Assistant: The current time is {current_time}.")
        res = f"Current time is {current_time}"

    elif action_type == "help":
        show_help()
        res = "Displayed help"

    elif action_type == "remember":
        save_personal_memory(target, action.get("value", ""))
        res = f"Remembered {target}"

    elif action_type == "recall":
        value = get_personal_memory(target)
        if value:
            print(f"Assistant: Your {target} is {value}.")
            res = f"{target} is {value}"
        else:
            print(f"Assistant: I don't have anything saved for {target}.")
            res = f"No memory for {target}"

    elif action_type == "chat":
        resp = action.get("response", "I am ready.")
        print(f"Assistant: {resp}")
        res = resp

    elif action_type == "web_search":
        results = web_search(target)

        if results and not results[0].get("error"):
            summary = summarize_search_results(target, results)

            if summary:
                print("Assistant: Web search summary:")
                print(summary)
                print()
            else:
                print("Assistant: I found results, but could not generate a summary.")

            print("Sources:")
            for item in results:
                print(f"- {item.get('title', '')}")
                print(f"  {item.get('url', '')}")

            res = f"Found {len(results)} web search results for {target}"

        else:
            error = results[0].get("error", "Unknown search error") if results else "No results"
            print(f"Assistant: Web search failed: {error}")
            res = f"Web search failed for {target}"

    # Record action in security audit log
    status = "SUCCESS" if res and not str(res).startswith("Failed") and not str(res).startswith("Invalid") else "FAILED"
    memory_manager.log_action(action_type, target, status, str(res))
    return res

def save_personal_memory(key, value):
    norm_key = memory_manager.normalize_key(key)
    memory_manager.save_fact(norm_key, value)
    personal_memory[norm_key] = value

    try:
        with open(PERSONAL_MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(personal_memory, file, indent=2)
    except Exception:
        pass

    print(f"Assistant: I will remember that your {norm_key.replace('_', ' ')} is {value}.")


def get_personal_memory(key):
    norm_key = memory_manager.normalize_key(key)
    val = memory_manager.get_fact(norm_key)
    if val:
        return val
    return personal_memory.get(norm_key) or personal_memory.get(key)
def ask_local_ai(user_message):
    system_prompt = """
You are the command interpreter for a personal Windows AI assistant.

Your primary job is to understand the USER'S INTENT from natural language and convert it into a safe JSON plan containing one or more actions.

IMPORTANT:
- Understand what the user means, not the exact words they use.
- Treat natural-language variations, polite requests, indirect requests, and conversational wording as equivalent when they express the same intent.
- Extract the requested action and its target from the user's complete sentence before selecting an action.
- Never require the user to use the exact wording shown in the examples.
- Do NOT depend on exact phrases, keywords, sentence structure, or the examples below.
- The examples are only demonstrations. They are NOT a list of required phrases.
- Different sentences with the same meaning must produce the same action.
- Handle normal conversational wording, polite requests, short commands, questions, and indirect requests.
- Infer the intended allowed application, folder, or operation when the meaning is clear.
- Never invent an application, folder, personal fact, or capability.
- If the request cannot safely be mapped to an allowed action, use the "chat" action.
- Always choose the safest valid action.
- Return exactly ONE JSON object containing an "actions" array.
- The "actions" array must contain one or more safe actions in the exact order they should be executed.
- Return VALID JSON only. Never return explanations, markdown, or extra text.
- NEVER add an action that the user did not explicitly request or that is not required to complete the request.

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

2. MOVE MOUSE

Use when the user explicitly asks you to move the mouse pointer/cursor.

JSON:
{"action":"move_mouse","target":"center"}

TARGET RULES:

- If the user gives exact X,Y coordinates, return those exact coordinates.
- If the user says "center", "middle of the screen", or equivalent, return:
  {"action":"move_mouse","target":"center"}
- If the user says "top left", return:
  {"action":"move_mouse","target":"top-left"}
- If the user says "top right", return:
  {"action":"move_mouse","target":"top-right"}
- If the user says "bottom left", return:
  {"action":"move_mouse","target":"bottom-left"}
- If the user says "bottom right", return:
  {"action":"move_mouse","target":"bottom-right"}

IMPORTANT:

- NEVER invent coordinates.
- NEVER convert "center" into coordinates.
- NEVER use 500,300 or any other example coordinates unless the user explicitly gives those coordinates.
- The Python program calculates semantic screen positions such as center and corners.
- Preserve exact coordinates when the user explicitly provides them.
- If the user asks to move the mouse but gives no position, use the "chat" action and ask for the position.
- Do not choose "open_app" for a mouse movement request.
- Do not infer a mouse position from an application name.
3. CLOSE APPLICATION
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

4. OPEN FOLDER
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

5. LIST FILES
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

5.5 COUNT FILES

Use when the user wants to know HOW MANY files are inside an allowed folder.

JSON:

{"action":"count_files","target":"downloads"}

Examples:

"how many files are in Downloads"
"how many files do I have in Downloads"
"count the files in my Downloads folder"
"tell me the number of files in Downloads"
"how many items are in my Documents folder"

These mean count_files.

IMPORTANT:

If the user asks to SEE or LIST the files, use list_files.
If the user asks HOW MANY files there are, use count_files.
If the user asks to OPEN or GO TO the folder, use open_folder.

6. WEB SEARCH

Use when the user asks for information that requires searching the current internet.

Examples:
- "search the web for the latest AI news"
- "find the latest news about NVIDIA"
- "search for Python 3.13 documentation"
- "look up today's weather"
- "find information about a new laptop"
- "what is the latest version of Ollama"
- "search online for this"

JSON:
{"action":"web_search","target":"latest AI news"}

IMPORTANT:
- Use web_search when the user explicitly asks to search, look up, find online, or search the web.
- Use web_search when the user asks for current or latest information that may have changed.
- Put the complete search query in target.
- Do NOT use web_search for normal conversation or questions that can be answered without an internet search.
- Do NOT invent search results.
- web_search only searches the internet; it does not execute commands or open applications.
- If the user asks to search the web and summarize, explain, or report the search results, use ONLY the web_search action.
- Do NOT add a separate chat action for summarizing search results.
- The web_search action automatically summarizes the retrieved results.

7. LIST RUNNING APPLICATIONS
Use when the user asks what applications, programs, or apps are currently running or open on the computer.

JSON:
{"action":"list_running_apps","target":""}

Examples:
"what apps are currently running"
"what programs are open"
"show me the applications running on my computer"
"which apps are open right now"
"tell me what is currently running"

These mean list_running_apps.

7.5 CURRENT TIME

Use when the user asks for the current time, asks what time it is, or asks to know the time right now.

JSON:

{"action":"time","target":""}

Examples:

"what time is it"
"what is the current time"
"tell me the time"
"can you tell me what time it is"
"what's the time right now"

These all mean time.

7. CREATE FOLDER
Use when the user wants to create a new folder.

JSON:
{"action":"create_folder","target":"MyFolder"}

Only create folders inside the allowed Documents location.

8. HELP

Use the help action ONLY when the user explicitly asks for:
- help
- available commands
- what commands can I use
- show me the commands
- list your commands
- how do I use you

Do NOT use help for normal conversation.

For questions such as:
- what can you do for me
- who are you
- tell me about yourself
- what are you capable of
- can you explain what you do

use NORMAL CONVERSATION instead.

JSON:
{"action":"help","target":""}

9. SAVE PERSONAL MEMORY
Use ONLY when the user explicitly asks you to remember something.

JSON:
{"action":"remember","target":"favorite_game","value":"Valorant"}

Never invent personal information.

10. RETRIEVE PERSONAL MEMORY
Use when the user asks about something that may have been saved in personal memory.

JSON:
{"action":"recall","target":"favorite_game"}

MEMORY RECALL RULES:
- If the user asks about their own preference, fact, choice, or information that may have been saved in personal memory, ALWAYS use "recall" first.
- Do NOT use "chat" for questions about the user's saved personal information.
- Examples:
  "What is my favorite programming language?" -> {"action":"recall","target":"favorite_language"}
  "Which game do I like?" -> {"action":"recall","target":"favorite_game"}
  "What color do I prefer?" -> {"action":"recall","target":"favorite_color"}
- If the requested information is not saved, still use "recall". The Python memory system will report that no memory exists.
- Never say that you do not have access to the user's personal information.
- Never invent a personal fact.

11. NORMAL CONVERSATION
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
MULTI-ACTION RULES:

- A single user sentence may contain multiple requested actions.
- Identify EVERY action the user explicitly requests.
- Return ALL requested actions in the "actions" array, in the same order as the user's request.
- Do not stop after identifying the first action.
- Example:
  User: "Open my Downloads folder and show me the files inside."
  JSON:
  {"actions":[
    {"action":"open_folder","target":"downloads"},
    {"action":"list_files","target":"downloads"}
  ]}
- Example:
  User: "Launch Chrome, move my mouse to 500,300, and open Downloads."
  JSON:
  {"actions":[
    {"action":"open_app","target":"chrome"},
    {"action":"move_mouse","target":"500,300"},
    {"action":"open_folder","target":"downloads"}
  ]}
- If the user asks to open something AND show/list/check its contents, return both actions.
- Never omit a requested action just because another action appears first.
Always choose the action based on the user's INTENT.
"""
    try:
        # Context Injection: inject known user facts into the system prompt for personal intelligence
        known_facts = memory_manager.get_all_facts()
        if known_facts:
            facts_text = "\n".join(f"- {k}: {v}" for k, v in known_facts.items())
            system_prompt += f"\nKNOWN USER PREFERENCES & FACTS:\n{facts_text}\n"

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )
        ai_start_time = time.perf_counter()
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            format={
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "open_app",
                            "close_app",
                            "move_mouse",
                            "type_text",
                            "press_key",
                            "open_folder",
                            "list_files",
                            "count_files",
                            "list_running_apps",
                            "create_folder",
                            "time",
                            "help",
                            "remember",
                            "recall",
                            "chat",
                            "web_search"
                        ]
                    },
                    "target": {
                        "type": "string"
                    },
                    "value": {
                        "type": "string"
                    },
                    "response": {
                        "type": "string"
                    }
                },
                "required": ["action", "target"],
                "additionalProperties": False
            }
        }
    },
    "required": ["actions"],
    "additionalProperties": False
},
            
            think=False
        )
        ai_elapsed_time = time.perf_counter() - ai_start_time
        print(f"AI processing time: {ai_elapsed_time:.2f} seconds.")
        content = response["message"]["content"]
        action = json.loads(content)
        # Remove redundant chat actions when web search already provides the summary.
        if isinstance(action, dict) and isinstance(action.get("actions"), list):
            if any(item.get("action") == "web_search" for item in action["actions"] if isinstance(item, dict)):
                action["actions"] = [
                    item for item in action["actions"]
                    if not (
                        isinstance(item, dict)
                        and item.get("action") == "chat"
                    )
                ]
        print("AI ACTION:", action)

        # Safety guard: reject unrelated actions for destructive requests
        destructive_words = (
            "delete",
            "erase",
            "wipe",
            "destroy",
            "format",
            "uninstall",
            "permanently remove",
        )

        if any(word in user_message.lower() for word in destructive_words):
            print("Assistant: This request requires a supported destructive action and was blocked for safety.")
            return

        execute_action(action)
        # Record conversation turns in SQLite memory
        memory_manager.add_conversation_turn("user", user_message)
        if isinstance(action, dict):
            memory_manager.add_conversation_turn("assistant", json.dumps(action))

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

    # Fast check for running applications query
    running_apps_patterns = [
        r"\brunning apps\b",
        r"\bopen apps\b",
        r"\brunning programs\b",
        r"\bopen programs\b",
        r"\bwhat apps are open\b",
        r"\bwhich apps are open\b",
        r"\bwhat is currently running\b",
        r"\blist running apps\b"
    ]
    if any(re.search(pat, command_lower) for pat in running_apps_patterns):
        return execute_action({
            "action": "list_running_apps",
            "target": ""
        })

    # FAST INTENT DETECTION
    # Handle obvious commands without calling the local AI.

    direct_app_intents = {
        "chrome": ["chrome", "google chrome"],
        "notepad": ["notepad"],
        "calculator": ["calculator", "calc"],
        "explorer": ["file explorer", "explorer"]
    }

    direct_folder_intents = {
        "downloads": ["downloads", "download folder"],
        "documents": ["documents", "document folder"],
        "desktop": ["desktop"],
        "pictures": ["pictures", "picture folder"],
        "videos": ["videos", "video folder"],
        "music": ["music", "music folder"]
    }

    # Detect negation words (e.g. "don't open chrome")
    negation_detected = bool(re.search(r"\b(?:don't|do not|never|stop|avoid|not)\b", command_lower))

    # Words that strongly indicate opening an application/folder.
    open_words = {
        "open", "launch", "start", "run"
    }

    # Use word boundary checks to avoid partial matches (e.g. "calc" matching "calculus")
    mentioned_apps = sum(
        any(re.search(rf"\b{re.escape(name)}\b", command_lower) for name in names)
        for names in direct_app_intents.values()
    )

    mentioned_folders = sum(
        any(re.search(rf"\b{re.escape(name)}\b", command_lower) for name in names)
        for names in direct_folder_intents.values()
    )

    multiple_targets = (mentioned_apps + mentioned_folders) > 1
    # Send multi-target natural-language requests to the local AI.
    # This lets the AI understand the complete user intent.
    if multiple_targets:
        return ask_local_ai(command)
    # Send compound natural-language requests to the local AI.
    compound_request = any(
        phrase in f" {command_lower} "
        for phrase in (
            " and ",
            " then ",
            " and then ",
            " also ",
            " after that ",
            " followed by ",
        )
    )

    if compound_request:
        return ask_local_ai(command)

    # Detect fast CLOSE APP requests
    close_words = [r"\bclose\b", r"\bquit\b", r"\bexit\b", r"\bshut down\b", r"\bterminate\b"]
    is_close_request = any(re.search(cw, command_lower) for cw in close_words)

    if not negation_detected and not multiple_targets and is_close_request:
        for target, names in direct_app_intents.items():
            if any(re.search(rf"\b{re.escape(name)}\b", command_lower) for name in names):
                return execute_action({
                    "action": "close_app",
                    "target": target
                })

    # Detect obvious OPEN APP requests.
    if not negation_detected and not multiple_targets and any(word in command_lower.split() for word in open_words):
        for target, names in direct_app_intents.items():
            if any(re.search(rf"\b{re.escape(name)}\b", command_lower) for name in names):
                return execute_action({
                    "action": "open_app",
                    "target": target
                })

        # Detect obvious OPEN FOLDER requests.
        for target, names in direct_folder_intents.items():
            if any(re.search(rf"\b{re.escape(name)}\b", command_lower) for name in names):
                return execute_action({
                    "action": "open_folder",
                    "target": target
                })
                # FAST FILE OPERATIONS
    # Handle clear list/count requests without calling the local AI.

    detected_folder = None

    for target, names in direct_folder_intents.items():
        if any(name in command_lower for name in names):
            detected_folder = target
            break

    if detected_folder and not multiple_targets:

        # Count files
        if (
            "how many files" in command_lower
            or "how many file" in command_lower
            or "count files" in command_lower
            or "number of files" in command_lower
        ):
            execute_action({
                "action": "count_files",
                "target": detected_folder
            })
            return

        # List/show files
        if (
            "list files" in command_lower
            or "what files" in command_lower
            or "what's in" in command_lower
            or "whats in" in command_lower
            or "what is in" in command_lower
            or "show me what's" in command_lower
            or "show me whats" in command_lower
        ):
            execute_action({
                "action": "list_files",
                "target": detected_folder
            })
            return

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
        return
            # Direct exact commands for common apps
    direct_apps = {
        "calculator": "calculator",
        "notepad": "notepad",
        "chrome": "chrome",
        "file explorer": "explorer",
        "explorer": "explorer"
    }

    # Direct exact commands for common folders
    direct_folders = {
        "downloads": "downloads",
        "documents": "documents",
        "desktop": "desktop",
        "pictures": "pictures",
        "videos": "videos",
        "music": "music"
    }

    # Keep exact simple commands fast and deterministic
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
    
         
    # Let local AI understand everything else
    ask_local_ai(command)

def main():
    print("Loading local AI...")
    try:
        ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "Reply with OK only."}]
        )
        print("Local AI ready.")
    except Exception as error:
        print(f"Warning: Could not contact local AI ({error}).")
        print("Please ensure the Ollama service is running and 'qwen3:4b' is installed.")
    print("========================================")
    print("        MY PERSONAL ASSISTANT")
    print("========================================")
    print("Assistant is online.")
    print("Local AI: ENABLED")
    print("Computer control: ENABLED")
    print("File control: ENABLED")
    print("AI model: qwen3:1.7b")
    print()
    print("Type 'help' to see commands.")
    print("Type 'exit' to shut down.")
    print()

    while True:
        command = input("You: ")

        start_time = time.perf_counter()

        result = process_command(command)

        elapsed_time = time.perf_counter() - start_time
        print(f"Total task time: {elapsed_time:.2f} seconds.")

        if result == "exit":
            break


if __name__ == "__main__":
    main()