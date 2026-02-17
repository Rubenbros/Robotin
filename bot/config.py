import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
TEMP_DIR = DATA_DIR / "temp"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

CLAUDE_PROJECTS_DIR = Path(os.getenv("CLAUDE_PROJECTS_DIR", str(Path.home() / "ClaudeProjects")))
CLAUDE_SKILLS_DIR = Path(os.getenv("CLAUDE_SKILLS_DIR", str(Path.home() / ".claude" / "skills")))

STANDALONE_PROJECTS: dict[str, str] = {
    # "nombre": r"C:\ruta\al\proyecto",
}

CLAUDE_MAX_TURNS = 0  # 0 = sin límite de turnos
CLAUDE_TIMEOUT = 1800  # 30 minutos (solo subprocess fallback)
CLAUDE_PERMISSION_MODE = "bypassPermissions"

WHISPER_MODEL = "small"
WHISPER_LANGUAGE = "es"

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

DANGEROUS_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "format ",
    "shutdown",
    "reboot",
    "printenv",
    "env ",
    "del /f /s /q",
    "rmdir /s /q C:\\",
]
