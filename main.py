import os
import subprocess
import shutil
import json
import time
import threading
import re
import pyttsx3
from datetime import datetime
from pathlib import Path
import ollama
import pyautogui
import memory_manager
from ddgs import DDGS
import ctypes
import speech_recognition as sr


# Text-to-speech engine
import subprocess


def speak_text(text):
    """Speak assistant responses using Windows' native speech engine."""
    if not text:
        return

    try:
        safe_text = str(text).replace("'", "''")

        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Speak('{safe_text}'); "
            "$speaker.Dispose()"
        )

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command
            ],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False
        )

    except Exception as error:
        print(f"TTS error: {error}")


def speak_text_async(text):
    """Speak without blocking command execution."""
    if not text:
        return

    threading.Thread(
        target=speak_text,
        args=(str(text),),
        daemon=True
    ).start()

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
OLLAMA_CLIENT = ollama.Client(host="http://127.0.0.1:11434", timeout=30)
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

        response = OLLAMA_CLIENT.chat(
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
def resolve_folder_path(folder_name):
    """Resolve an allowed folder or a subfolder inside an allowed location."""
    folders = get_folders()
    folder_name = folder_name.strip()

    # Direct approved folder
    key = folder_name.lower()
    if key in folders:
        return folders[key]

    # Allow subfolders inside approved locations
    normalized = folder_name.replace("\\", "/")

    for base_name, base_path in folders.items():
        prefix = base_name + "/"

        if normalized.lower().startswith(prefix):
            relative_path = normalized[len(prefix):]
            candidate = os.path.abspath(
                os.path.join(base_path, relative_path)
            )

            base_path_abs = os.path.abspath(base_path)

            # Security: never allow escaping the approved folder
            if os.path.commonpath([candidate, base_path_abs]) == base_path_abs:
                return candidate
        # Allow relative folders inside Documents.
    # Example: "JARVIS_Test" means Documents/JARVIS_Test.
    documents_path = os.path.abspath(folders["documents"])
    candidate = os.path.abspath(
        os.path.join(documents_path, folder_name)
    )

    try:
        if os.path.commonpath([candidate, documents_path]) == documents_path:
            return candidate
    except ValueError:
        pass
    return None

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
    
APP_ID_CACHE = {}

# Deterministic Windows applications. These are resolved directly instead of
# using a generic Start Menu search, which can return the wrong AppID.
COMMON_APP_EXECUTABLES = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
}


BLOCKED_APP_NAMES = {
    "cmd", "cmd.exe", "command prompt",
    "powershell", "powershell.exe", "windows powershell",
    "pwsh", "pwsh.exe", "regedit", "regedit.exe", "registry editor",
    "diskpart", "diskpart.exe", "format", "format.com",
    "taskkill", "taskkill.exe", "mshta", "mshta.exe",
    "wscript", "wscript.exe", "cscript", "cscript.exe",
    "python", "python.exe", "python3", "python3.exe",
    "bash", "bash.exe", "wsl", "wsl.exe", "zsh", "zsh.exe",
    "curl", "curl.exe", "wget", "wget.exe",
}


def _normalize_app_name(app_name):
    return re.sub(r"\s+", " ", str(app_name).strip()).lower()


def find_start_menu_app(app_name):
    """Return the first matching Windows Start Menu AppID, or None."""
    normalized = _normalize_app_name(app_name)
    if not normalized or normalized in BLOCKED_APP_NAMES:
        return None

    script = (
        "$name=$args[0]; "
        "Get-StartApps | "
        "Where-Object { $_.Name -like ('*' + $name + '*') } | "
        "Select-Object -First 1 -ExpandProperty AppID"
    )

    if normalized in APP_ID_CACHE:
        return APP_ID_CACHE[normalized]

    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                script, normalized,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        app_id = result.stdout.strip()
        if app_id:
            APP_ID_CACHE[normalized] = app_id
        return app_id or None
    except Exception:
        return None


def is_installed_app(app_name):
    """Check whether an application can be safely resolved before launching it."""
    normalized = _normalize_app_name(app_name)
    if not normalized or normalized in BLOCKED_APP_NAMES:
        return False

    # Deterministic Windows apps are checked directly.
    if normalized in COMMON_APP_EXECUTABLES:
        return bool(shutil.which(COMMON_APP_EXECUTABLES[normalized]))

    if find_start_menu_app(normalized):
        return True
    return bool(shutil.which(normalized))

def open_application(app_name):
    """Find and launch an installed Windows application dynamically."""

    app_name = str(app_name).strip()

    if not app_name:
        print("Assistant: Please specify an application.")
        return False

    def normalize(value):
        value = str(value).lower().strip()

        for suffix in (
            ".exe",
            ".lnk",
            "application",
            "app",
            "program",
            "ide",
            "player",
            "browser",
            "launcher",
            "client",
        ):
            if value.endswith(suffix):
                value = value[:-len(suffix)]

        value = value.replace("_", " ")
        value = value.replace("-", " ")

        return " ".join(value.split())

    requested = normalize(app_name)

    if requested in BLOCKED_APP_NAMES:
        print(f"Assistant: I cannot launch the system command '{app_name}'.")
        return False

    # ============================================================
    # 1. WINDOWS START MENU APPLICATION DISCOVERY
    # ============================================================

    try:
        powershell_script = r"""
$apps = Get-StartApps | Select-Object Name, AppID
$apps | ConvertTo-Json -Compress
"""

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)

            if isinstance(data, dict):
                data = [data]

            exact_match = None
            partial_match = None

            for item in data:
                name = str(item.get("Name", "")).strip()
                app_id = str(item.get("AppID", "")).strip()

                if not name or not app_id:
                    continue

                normalized_name = normalize(name)

                # Exact match first.
                if normalized_name == requested:
                    exact_match = (name, app_id)
                    break

                # Partial match only as fallback.
                if (
                    requested in normalized_name
                    or normalized_name in requested
                ):
                    if partial_match is None:
                        partial_match = (name, app_id)

            match = exact_match or partial_match

            if match:
                display_name, app_id = match

                try:
                    subprocess.Popen(
                        [
                            "explorer.exe",
                            f"shell:AppsFolder\\{app_id}",
                        ],
                        shell=False,
                    )

                    print(f"Assistant: Opening {display_name}.")
                    return True

                except Exception:
                    pass

    except Exception:
        pass

    # ============================================================
    # 2. WINDOWS START MENU SHORTCUT DISCOVERY
    # ============================================================

    try:
        start_menu_paths = [
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",

            Path(os.environ.get("PROGRAMDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",
        ]

        candidates = []

        for start_root in start_menu_paths:
            if not start_root.is_dir():
                continue

            try:
                for shortcut in start_root.rglob("*.lnk"):
                    shortcut_name = normalize(shortcut.stem)

                    if shortcut_name == requested:
                        candidates.insert(0, shortcut)

                    elif (
                        requested in shortcut_name
                        or shortcut_name in requested
                    ):
                        candidates.append(shortcut)

            except Exception:
                continue

        for shortcut in candidates:
            try:
                os.startfile(str(shortcut))
                print(f"Assistant: Opening {shortcut.stem}.")
                return True
            except Exception:
                continue

    except Exception:
        pass

    # ============================================================
    # 3. WINDOWS APP PATHS REGISTRY
    # ============================================================

    try:
        import winreg

        registry_locations = [
            (
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\App Paths",
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\App Paths",
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
            ),
        ]

        for hive, registry_path in registry_locations:
            try:
                with winreg.OpenKey(hive, registry_path) as root_key:
                    index = 0

                    while True:
                        try:
                            subkey_name = winreg.EnumKey(root_key, index)
                            index += 1
                        except OSError:
                            break

                        normalized_key = normalize(
                            Path(subkey_name).stem
                        )

                        if (
                            normalized_key == requested
                            or requested in normalized_key
                            or normalized_key in requested
                        ):
                            try:
                                with winreg.OpenKey(
                                    root_key,
                                    subkey_name,
                                ) as app_key:

                                    executable, _ = winreg.QueryValueEx(
                                        app_key,
                                        None,
                                    )

                                    executable = str(executable).strip(
                                        '" '
                                    )

                                    executable_path = Path(executable)

                                    if executable_path.is_file():
                                        subprocess.Popen(
                                            [str(executable_path)],
                                            shell=False,
                                        )

                                        print(
                                            f"Assistant: Opening {app_name}."
                                        )
                                        return True

                            except Exception:
                                continue

            except Exception:
                continue

    except Exception:
        pass

    # ============================================================
    # 4. SEARCH COMMON WINDOWS APPLICATION LOCATIONS
    # ============================================================

    search_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path(os.environ.get("PROGRAMFILES", "")),
        Path(os.environ.get("PROGRAMFILES(X86)", "")),
    ]

    possible_executables = []

    for root in search_roots:
        if not root.is_dir():
            continue

        try:
            # Search only a limited depth first.
            for path in root.glob("*"):
                if not path.is_dir():
                    continue

                folder_name = normalize(path.name)

                if (
                    requested == folder_name
                    or requested in folder_name
                    or folder_name in requested
                ):
                    possible_executables.extend(
                        path.rglob("*.exe")
                    )

        except Exception:
            continue

    # Prefer executable names that closely match the requested app.
    possible_executables.sort(
        key=lambda p: (
            0 if normalize(p.stem) == requested else
            1 if requested in normalize(p.stem) else
            2
        )
    )

    for executable in possible_executables:
        try:
            if executable.is_file():
                subprocess.Popen(
                    [str(executable)],
                    shell=False,
                )

                print(f"Assistant: Opening {app_name}.")
                return True

        except Exception:
            continue

    # ============================================================
    # 5. SEARCH WINDOWS PATH
    # ============================================================

    try:
        executable = shutil.which(app_name)

        if executable:
            subprocess.Popen(
                [executable],
                shell=False,
            )

            print(f"Assistant: Opening {app_name}.")
            return True

    except Exception:
        pass

    # ============================================================
    # APPLICATION NOT FOUND
    # ============================================================

    print(
        f"Assistant: I could not find an installed application "
        f"matching '{app_name}'."
    )

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
    folder_name = str(folder_name).strip().strip('"\'')

    # Standard Windows user folders.
    folder_key = folder_name.lower()
    if folder_key in folders:
        path = folders[folder_key]
        if os.path.isdir(path):
            os.startfile(path)
            print(f"Assistant: Opening your {folder_name} folder.")
            return True
        print(f"Assistant: I could not find your {folder_name} folder.")
        return False

    # Path-style/custom folders are resolved safely inside Documents.
    resolved = resolve_folder_path(folder_name)
    if resolved and os.path.isdir(resolved):
        os.startfile(resolved)
        print(f"Assistant: Opening {folder_name}.")
        return True

    # Backward-compatible fallback: search approved roots by folder name.
    search_roots = [
        folders["documents"], folders["downloads"], folders["desktop"],
        folders["pictures"], folders["videos"], folders["music"],
    ]
    target_basename = folder_name.replace("\\", "/").rstrip("/").split("/")[-1].lower()
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        try:
            for current_root, dirs, _files in os.walk(root):
                for directory in dirs:
                    if directory.lower() == target_basename:
                        path = os.path.join(current_root, directory)
                        os.startfile(path)
                        print(f"Assistant: Opening {folder_name}.")
                        return True
        except Exception:
            continue

    print(f"Assistant: I could not find the '{folder_name}' folder.")
    return False

def list_files(folder_name):
    path = resolve_folder_path(folder_name)

    if path is None:
        print(f"Assistant: I don't have access to '{folder_name}'.")
        return []

    if not os.path.exists(path):
        print(f"Assistant: I could not find '{folder_name}'.")
        return []

    try:
        items = os.listdir(path)

        print(f"\nAssistant: Contents of {folder_name}:")
        if not items:
            print("  - The folder is empty.")
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
    folder_name = str(folder_name).strip()

    if not folder_name:
        print("Assistant: Please provide a folder name.")
        return False

    for part in Path(folder_name).parts:
        if re.search(r'[<>:"|?*]', part):
            print("Assistant: Folder name contains invalid characters.")
            return False

    docs_dir = Path(os.path.expanduser("~")) / "Documents"
    target_path = (docs_dir / folder_name).resolve()

    try:
        target_path.relative_to(docs_dir.resolve())
    except ValueError:
        print("Assistant: Blocked folder creation outside your Documents folder.")
        return False

    if target_path.exists():
        print("Assistant: That folder already exists.")
        return False

    try:
        target_path.mkdir(parents=True, exist_ok=False)
        print(f"Assistant: Created '{folder_name}' inside your Documents folder.")
        return True
    except Exception as error:
        print("Assistant: I could not create the folder.")
        print(f"System error: {error}")
        return False


def create_file(file_name):
    file_name = file_name.strip()

    if not file_name:
        print("Assistant: Please provide a file name.")
        return False

    # Prevent invalid Windows filename characters
    if re.search(r'[<>:"\\|?*]', file_name):
        print("Assistant: File name contains invalid characters.")
        return False

    docs_dir = Path(os.path.expanduser("~")) / "Documents"

    # Allow a path such as JARVIS_Test/test.txt
    target_path = (docs_dir / file_name).resolve()

    # Keep the file strictly inside Documents
    try:
        target_path.relative_to(docs_dir.resolve())
    except ValueError:
        print("Assistant: Blocked file creation outside your Documents folder.")
        return False

    # Make sure the parent folder exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists():
        print(f"Assistant: '{file_name}' already exists.")
        return False

    try:
        target_path.touch()

        print(f"Assistant: Created file '{file_name}' inside your Documents folder.")
        return True

    except Exception as error:
        print("Assistant: I could not create the file.")
        print(f"System error: {error}")
        return False



def write_file(file_name, content):
    """Write text safely to a file inside Documents."""
    file_name = file_name.strip().strip('"\'')
    if not file_name:
        print("Assistant: Please provide a file name.")
        return False

    relative_name = file_name.replace("\\", "/")
    docs_dir = Path(os.path.expanduser("~")) / "Documents"
    target_path = (docs_dir / relative_name).resolve()

    try:
        target_path.relative_to(docs_dir.resolve())
    except ValueError:
        print("Assistant: Blocked file write outside Documents.")
        return False

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(str(content), encoding="utf-8")
        print(f"Assistant: Wrote the requested text to '{file_name}'.")
        return True
    except Exception as error:
        print("Assistant: I could not write the file.")
        print(f"System error: {error}")
        return False


def read_file(file_name):
    """Read a text file safely from inside the user's Documents folder."""
    file_name = file_name.strip().strip('"\'')
    if not file_name:
        print("Assistant: Please provide a file name.")
        return ""

    relative_name = file_name.replace("\\", "/")
    docs_dir = Path(os.path.expanduser("~")) / "Documents"
    target_path = (docs_dir / relative_name).resolve()

    try:
        target_path.relative_to(docs_dir.resolve())
    except ValueError:
        print("Assistant: Blocked file read outside your Documents folder.")
        return ""

    if not target_path.exists():
        print(f"Assistant: I could not find '{file_name}'.")
        return ""

    if not target_path.is_file():
        print(f"Assistant: '{file_name}' is not a file.")
        return ""

    try:
        content = target_path.read_text(encoding="utf-8")
        print(f"\nAssistant: Contents of {file_name}:")
        print(content if content else "  - The file is empty.")
        print()
        return content
    except UnicodeDecodeError:
        print("Assistant: This file is not a UTF-8 text file.")
        return ""
    except Exception as error:
        print(f"Assistant: I could not read the file: {error}")
        return ""

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
        "open_app", "type_text", "press_key", "hotkey", "move_mouse",
        "close_app", "open_folder", "list_files", "count_files",
        "list_running_apps", "create_folder", "create_file", "write_file",
        "read_file", "time", "help", "remember", "recall", "chat", "web_search"
    }

    if action_type not in allowed_actions:
        print(f"Assistant: Blocked unknown action '{action_type}'.")
        return False

    # Opening an application is allowed when Windows can resolve it as an
    # installed Start Menu app or a real executable on PATH. High-risk command
    # and system-management tools are blocked by BLOCKED_APP_NAMES.
    if action_type == "open_app":
        target_clean = _normalize_app_name(target)
        if not target_clean:
            print("Assistant: No application was specified.")
            return False
        if not is_installed_app(target_clean):
            print(f"Assistant: Blocked unknown or unavailable application '{target}'.")
            return False
        return True

    # Closing apps stays restricted because force-terminating arbitrary
    # processes is materially more dangerous than launching an app.
    if action_type == "close_app":
        target_clean = _normalize_app_name(target)
        if target_clean not in set(CLOSE_APPS.keys()):
            print(f"Assistant: I am not allowed to close '{target}'.")
            return False
        return True

    # Approved folders are the user's normal folders and their existing
    # subfolders. Absolute paths and traversal are always blocked.
    if action_type in {"open_folder", "list_files", "count_files"}:
        target_clean = str(target).strip().strip('"\'').replace("\\", "/")
        if not target_clean:
            print("Assistant: No folder was specified.")
            return False

        target_path = Path(target_clean)
        blocked_parts = {"system32", "program files", "appdata", "windows", "programdata"}
        if (
            target_path.is_absolute()
            or (len(target_clean) >= 3 and target_clean[1] == ":" and target_clean[2] == "/")
            or target_clean.startswith("/")
            or ".." in target_path.parts
            or any(part.lower() in blocked_parts for part in target_path.parts)
        ):
            print(f"Assistant: Blocked unsafe folder path '{target}'.")
            return False

        folders = get_folders()
        normalized = target_clean.lower()
        if normalized in folders:
            if os.path.isdir(folders[normalized]):
                return True
            print(f"Assistant: Folder '{target}' does not exist.")
            return False

        resolved = resolve_folder_path(target_clean)
        if resolved is None or not os.path.isdir(resolved):
            print(f"Assistant: Blocked unknown folder '{target}'.")
            return False

        resolved_abs = os.path.abspath(resolved)
        for base_path in folders.values():
            base_abs = os.path.abspath(base_path)
            try:
                if os.path.commonpath([resolved_abs, base_abs]) == base_abs:
                    return True
            except ValueError:
                continue

        print(f"Assistant: Blocked folder outside approved user folders '{target}'.")
        return False

    # Create/write operations are restricted to Documents and get a common
    # traversal/name/content-size check before their individual functions run.
    if action_type in {"create_file", "write_file"}:
        file_target = str(target).strip().strip('"\'').replace("\\", "/")
        if file_target.lower().startswith("documents/"):
            file_target = file_target[len("documents/"):]
        if not file_target or ".." in Path(file_target).parts:
            print(f"Assistant: Blocked unsafe file path '{target}'.")
            return False

        documents_path = Path(get_folders()["documents"]).resolve()
        file_path = (documents_path / file_target).resolve()
        try:
            file_path.relative_to(documents_path)
        except ValueError:
            print(f"Assistant: Blocked file path outside Documents '{target}'.")
            return False

        for part in Path(file_target).parts:
            if re.search(r'[<>:"|?*]', part):
                print(f"Assistant: Blocked invalid file name '{target}'.")
                return False

        if action_type == "write_file":
            value = action.get("value", "")
            if not isinstance(value, str) or len(value) > 1_000_000:
                print("Assistant: Blocked invalid or oversized file content.")
                return False
        return True

    # Reads are restricted to existing files inside Documents.
    if action_type == "read_file":
        file_target = str(target).strip().replace("\\", "/")
        if not file_target:
            print("Assistant: No file was specified.")
            return False
        if file_target.lower().startswith("documents/"):
            file_target = file_target[len("documents/"):]

        documents_path = Path(get_folders()["documents"]).resolve()
        file_path = (documents_path / file_target).resolve()
        try:
            file_path.relative_to(documents_path)
        except ValueError:
            print(f"Assistant: Blocked file read outside Documents '{target}'.")
            return False
        if not file_path.is_file():
            print(f"Assistant: Blocked unknown file '{target}'.")
            return False
        return True

    if action_type == "type_text":
        if not isinstance(target, str) or len(target) > 5_000:
            print("Assistant: Blocked invalid or oversized text input.")
            return False
        return True

    valid_keys = {
        "\"", "'", "\\", *"abcdefghijklmnopqrstuvwxyz0123456789",
        "enter", "esc", "escape", "tab", "space", "backspace", "delete",
        "home", "end", "pageup", "pagedown", "up", "down", "left", "right",
        "shift", "ctrl", "alt", "win", "command", "insert", "capslock",
        "numlock", "scrolllock", "pause", "printscreen",
        *[f"f{i}" for i in range(1, 13)],
        "decimal", "add", "subtract", "multiply", "divide", "separator",
    }

    if action_type == "press_key":
        key = str(target).strip().lower()
        if key not in valid_keys:
            print(f"Assistant: Blocked unsupported key '{target}'.")
            return False
        return True

    if action_type == "hotkey":
        keys = [key.strip().lower() for key in str(target).split("+") if key.strip()]
        if not keys or len(keys) > 4 or any(key not in valid_keys for key in keys):
            print(f"Assistant: Blocked unsupported hotkey '{target}'.")
            return False
        return True

    if action_type == "move_mouse":
        target_clean = str(target).strip().lower()
        if target_clean in {"center", "top-left", "top-right", "bottom-left", "bottom-right"}:
            return True
        try:
            x_text, y_text = target_clean.split(",", 1)
            int(x_text.strip())
            int(y_text.strip())
        except (ValueError, TypeError):
            print(f"Assistant: Blocked invalid mouse position '{target}'.")
            return False
        return True

    return True


def _execute_action(action):
    if not validate_action(action):
        return None

    # Handle multiple actions in the exact order requested.
    # Stop the sequence if an action fails instead of blindly continuing.
    if "actions" in action and isinstance(action["actions"], list):
        results = []

        for step in action["actions"]:
            if not isinstance(step, dict):
                continue

            result = execute_action(step)

            if result is None:
                print("Assistant: An action could not be completed. Stopping the remaining actions.")
                break

            result_text = str(result)
            results.append(result_text)

            failed_markers = (
                "Failed",
                "Blocked",
                "Invalid",
            )

            if result_text.startswith(failed_markers):
                print("Assistant: The previous action failed. Stopping the remaining actions.")
                break

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
        
    elif action_type == "hotkey":
        try:
            keys = [key.strip().lower() for key in target.split("+") if key.strip()]
            pyautogui.hotkey(*keys)
            print(f"Assistant: Pressed hotkey {target}.")
            res = f"Pressed hotkey {target}."
        except Exception:
            print("Assistant: Failed to press the requested hotkey.")
            res = "Failed to press the requested hotkey."
    
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
        success = create_folder(folder_name)
        res = f"Created folder {target}" if success else f"Failed to create folder {target}"

    elif action_type == "create_file":
        success = create_file(target)
        res = f"Created file {target}" if success else f"Failed to create {target}"

    elif action_type == "write_file":
        success = write_file(target, action.get("value", ""))
        res = f"Wrote to {target}" if success else f"Failed to write to {target}"

    elif action_type == "read_file":
        content = read_file(target)
        res = f"Read file {target}" if content != "" else f"Read file {target} (empty or unavailable)"

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
                # Keep the spoken response on one line so the GUI TTS
                # extraction receives the complete web-search answer.
                clean_summary = " ".join(str(summary).split())
                print(f"Assistant: {clean_summary}")
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
def execute_action(action):
    """Safely execute an AI-generated action."""
    try:
        return _execute_action(action)
    except Exception as e:
        action_type = action.get("action", "unknown") if isinstance(action, dict) else "unknown"
        target = action.get("target", "") if isinstance(action, dict) else ""

        error_message = f"Failed to execute action '{action_type}': {e}"

        print(f"Assistant: {error_message}")

        try:
            memory_manager.log_action(
                action_type,
                target,
                "FAILED",
                error_message
            )
        except Exception:
            pass

        return error_message

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

Application rules:
- The user may request ANY application installed on the Windows computer.
- Do not maintain or assume a fixed list of applications.
- Return the application name requested by the user as the "target".
- Preserve the user's intended application name.
- Do not invent an application that the user did not request.
- The Python application resolver will determine whether the application is installed and how to launch it.

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

TYPE TEXT
Use when the user explicitly asks the assistant to type text into the currently focused application.
JSON:
{"action":"type_text","target":"text to type"}

PRESS KEY / HOTKEY
Use when the user explicitly asks to press a keyboard key or key combination.
Examples:
{"action":"press_key","target":"enter"}
{"action":"hotkey","target":"ctrl+c"}
Do not invent keys or key combinations.

3. CLOSE APPLICATION
Use when the user wants to close an installed application.

JSON:
{"action":"close_app","target":"calculator"}

Application rules:
- The user may request ANY installed application.
- Do not maintain or assume a fixed list of applications.
- Return the application name requested by the user as the "target".
- Do not invent an application that the user did not request.
- The Python application resolver will determine whether the application exists and can be controlled.

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

7. CREATE FILE

Use when the user wants to create a new file.

Examples:
- "create a file named test.txt"
- "make a file called notes.txt"
- "create test.txt inside JARVIS_Test"
- "make JARVIS_Test/test.txt"

JSON:
{"action":"create_file","target":"test.txt"}

For a file inside a folder:
{"action":"create_file","target":"JARVIS_Test/test.txt"}

IMPORTANT:
- If the user asks to create a FILE, always use "create_file".
- If the user asks to create a FOLDER, use "create_folder".
- Never use "create_folder" for a file.
- A path containing a folder name does not mean the target itself is a folder.
- "create JARVIS_Test/test.txt" means create a FILE named test.txt inside JARVIS_Test.

7. CREATE FOLDER
Use when the user wants to create a new folder.

JSON:
{"action":"create_folder","target":"MyFolder"}

Only create folders inside the allowed Documents location.

7.25 READ FILE

Use when the user explicitly wants to read, display, show, or inspect the contents of a file.

JSON:
{"action":"read_file","target":"JARVIS_New/hello.txt"}

Examples:
- "read the file hello.txt inside Documents/JARVIS_New"
- "show me the contents of hello.txt in JARVIS_New"
- "read JARVIS_New/hello.txt"

IMPORTANT:
- Always use "read_file" for a request to read file contents.
- Do NOT use "open_folder" for a read-file request.
- Do NOT use "create_file" or "create_folder" for a read-file request.
- The target must be the file path relative to Documents.
- If the user says "Documents/JARVIS_New/hello.txt", return "JARVIS_New/hello.txt".

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
- Applications are dynamic and are resolved by the Python application resolver.
- For open_app and close_app, the target may be any application explicitly requested by the user.
- Do not restrict applications to examples shown in this prompt.

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
        response = OLLAMA_CLIENT.chat(
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
                            "hotkey",
                            "open_folder",
                            "list_files",
                            "count_files",
                            "list_running_apps",
                            "create_folder",
                            "create_file",
                            "write_file",
                            "read_file",
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
        # Safety/correction layer: enforce the user's requested file operation.
        if (
            "create a file" in user_message.lower()
            or "make a file" in user_message.lower()
        ):
            if isinstance(action, dict) and isinstance(action.get("actions"), list):

                # Find the actual filename requested by the user.
                import re

                filename_match = re.search(
                r'(?:named|called)\s+["\']?([A-Za-z0-9_.-]+\.(?:txt|py|html|css|js|json|csv|md|pdf|docx|xlsx|jpg|jpeg|png|gif))["\']?',
                user_message,
                re.IGNORECASE
            )

                if filename_match:
                    requested_filename = filename_match.group(1).strip()

                    # Find the folder mentioned after "inside" or "in".
                    # Find the folder/path mentioned after "inside" or "in".
                    folder_match = re.search(
                        r'\b(?:inside|in)\s+([A-Za-z0-9 _./\\-]+?)(?:\s+folder)?\s*$',
                        user_message,
                        re.IGNORECASE
                    )

                    if folder_match:
                        requested_folder = folder_match.group(1).strip()

                        # The file functions already work relative to Documents.
                        # Remove the Documents prefix if the user included it.
                        requested_folder = re.sub(
                            r'^Documents[\\/]',
                            '',
                            requested_folder,
                            flags=re.IGNORECASE
                        )

                        requested_target = f"{requested_folder}/{requested_filename}"
                    else:
                        requested_target = requested_filename

                    

                    # For a file request, keep ONLY the create_file action.
                    action["actions"] = [
                        {
                            "action": "create_file",
                            "target": requested_target
                        }
                    ]

                    print(
                        f"Assistant: Corrected file request -> {requested_target}"
                    )
        print("AI ACTION:", action)
        # Safety/correction layer for list-files requests.
        if "list files" in user_message.lower() or "show files" in user_message.lower():
            if isinstance(action, dict) and isinstance(action.get("actions"), list):
                import re

                list_folder_match = re.search(
                    r'\b(?:inside|in)\s+([A-Za-z0-9_./\\-]+?)(?:\s+folder)?\s*$',
                    user_message,
                    re.IGNORECASE
                )

                if list_folder_match:
                    requested_folder = list_folder_match.group(1).strip()

                    # list_files() works relative to Documents.
                    requested_folder = re.sub(
                        r'^Documents[\\/]',
                        '',
                        requested_folder,
                        flags=re.IGNORECASE
                    )

                    action["actions"] = [
                        {
                            "action": "list_files",
                            "target": requested_folder
                        }
                    ]

                    print(
                        f"Assistant: Corrected list-files request -> "
                        f"{requested_folder}"
                    )
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

def listen_for_voice():
    """Listen through the default microphone and convert speech to text."""
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("Assistant: Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=8
            )

        print("Assistant: Processing voice...")

        try:
            text = recognizer.recognize_google(audio)
            print(f"You (voice): {text}")
            return text.strip()

        except sr.UnknownValueError:
            print("Assistant: I couldn't understand what you said.")
            return ""

        except sr.RequestError as error:
            print(f"Assistant: Speech recognition service unavailable: {error}")
            return ""

    except sr.WaitTimeoutError:
        print("Assistant: I didn't hear anything.")
        return ""

    except Exception as error:
        print(f"Assistant: Microphone error: {error}")
        return ""

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
    # FAST PATH: list files in a specific folder/path.
    # This must run before the generic folder-intent detector,
    # otherwise "Documents/JARVIS_Test" gets mistaken for "Documents".

    # RELIABLE WRITE-FILE COMMANDS
    write_file_match = re.search(
        r'^\s*write\s+(?:"([^"]*)"|\'([^\']*)\')\s+into\s+(.+?)\s+inside\s+(.+?)\s*$',
        command,
        re.IGNORECASE
    )

    if write_file_match:
        content = write_file_match.group(1)
        if content is None:
            content = write_file_match.group(2)

        filename = write_file_match.group(3).strip().strip('"\'')
        folder = write_file_match.group(4).strip().strip('"\'')
        folder = re.sub(r'\s+folder\s*$', '', folder, flags=re.IGNORECASE).strip()
        folder = re.sub(r'^Documents[\\/]', '', folder, flags=re.IGNORECASE)

        requested_file = f"{folder}/{filename}".replace("\\", "/")
        print(f"Assistant: Direct write-file request -> {requested_file}")

        return execute_action({
            "action": "write_file",
            "target": requested_file,
            "value": content
        })

    # RELIABLE READ-FILE COMMANDS
    # Handle explicit file-reading requests without relying on the local model.
    read_file_match = re.search(
        r'^\s*(?:read|show|display)\s+(?:the\s+)?file\s+(.+?)\s*$',
        command,
        re.IGNORECASE
    )

    if read_file_match:
        requested_file = read_file_match.group(1).strip().strip('"\'')

        inside_match = re.search(
            r'^(.*?)\s+inside\s+(.+?)\s*$',
            requested_file,
            re.IGNORECASE
        )
        if inside_match:
            filename = inside_match.group(1).strip()
            folder = inside_match.group(2).strip().rstrip('/\\')
            requested_file = f"{folder}/{filename}"

        in_match = re.search(
            r'^(.*?)\s+in\s+(.+?)\s*$',
            requested_file,
            re.IGNORECASE
        )
        if in_match and "/" not in requested_file and "\\" not in requested_file:
            requested_file = f"{in_match.group(2).strip().rstrip('/\\')}/{in_match.group(1).strip()}"

        requested_file = re.sub(
            r'^Documents[\\/]',
            '',
            requested_file,
            flags=re.IGNORECASE
        ).replace("\\", "/")

        print(f"Assistant: Direct read-file request -> {requested_file}")
        return execute_action({
            "action": "read_file",
            "target": requested_file
        })

    list_path_match = re.search(
        r'^\s*(?:list|show)\s+(?:the\s+)?files?\s+'
        r'(?:inside|in|from|of)\s+(.+?)\s*$',
        command,
        re.IGNORECASE
    )

    if list_path_match:
        requested_folder = list_path_match.group(1).strip().strip('"\'')
        requested_folder = re.sub(
            r'\s+folder\s*$',
            '',
            requested_folder,
            flags=re.IGNORECASE
        ).strip()

        # The file functions work relative to Documents.
        # Remove the Documents prefix when the user explicitly includes it.
        requested_folder = re.sub(
            r'^Documents[\\/]',
            '',
            requested_folder,
            flags=re.IGNORECASE
        ).strip()
        print(
            f"Assistant: Direct list-files request -> {requested_folder}"
        )

        return execute_action({
            "action": "list_files",
            "target": requested_folder
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

    # RELIABLE OPEN-FOLDER PATH COMMANDS
    # Handle explicit filesystem paths deterministically instead of relying
    # on the small local model to infer the requested folder.
    # Examples:
    #   Open JARVIS_Test_Final/SubTest folder
    #   Open Documents/JARVIS_Test_Final/SubTest
    open_folder_match = re.search(
        r'^\s*(?:open|launch|start)\s+(?:the\s+)?(.+?)'
        r'(?:\s+folder)?\s*$',
        command,
        re.IGNORECASE
    )

    if open_folder_match and not negation_detected:
        requested_folder = open_folder_match.group(1).strip().strip("\"'")
        requested_folder = re.sub(
            r'^Documents[\\\\/]',
            '',
            requested_folder,
            flags=re.IGNORECASE
        ).strip().rstrip("\\\\")

        # Path-style folder requests are handled directly.
        if '/' in requested_folder or '\\\\' in requested_folder:
            print(
                f"Assistant: Direct open-folder request -> {requested_folder}"
            )
            return execute_action({
                "action": "open_folder",
                "target": requested_folder
            })

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

    ollama_ready = False

    for attempt in range(1, 6):
        try:
            OLLAMA_CLIENT.chat(
                model=MODEL,
                messages=[{"role": "user", "content": "Reply with OK only."}],
            )

            ollama_ready = True
            print("Local AI ready.")
            break

        except Exception as error:
            if attempt < 5:
                print(f"Waiting for Ollama... {attempt}/5")
                time.sleep(2)
            else:
                print(f"Warning: Could not contact local AI ({error}).")
                print(
                    "Please ensure the Ollama service is running "
                    "and 'qwen3:1.7b' is installed."
                )
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
        try:
            command = input("You: ")
        except KeyboardInterrupt:
            print("\nAssistant: Interrupted. Shutting down.")
            break
        except EOFError:
            print("\nAssistant: Input closed. Shutting down.")
            break

        start_time = time.perf_counter()

        result = process_command(command)

        elapsed_time = time.perf_counter() - start_time
        print(f"Total task time: {elapsed_time:.2f} seconds.")

        if result == "exit":
            break


if __name__ == "__main__":
    main()