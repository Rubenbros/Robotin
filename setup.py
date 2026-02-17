"""
Instalador interactivo para Claude Telegram Bot.
Ejecutar: python setup.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def banner():
    print()
    print("=" * 50)
    print("  Claude Telegram Bot — Instalador")
    print("=" * 50)
    print()
    print("Este asistente configurara el bot paso a paso.")
    print()


def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"{prompt}{hint}: ").strip()
    return value or default


def step_token() -> str:
    print("— Paso 1: Token del bot de Telegram —")
    print()
    print("Necesitas un token de @BotFather en Telegram:")
    print("  1. Abre Telegram y busca @BotFather")
    print("  2. Envia /newbot y sigue las instrucciones")
    print("  3. Copia el token que te da (formato: 123456:ABC-DEF...)")
    print()
    while True:
        token = ask("Pega tu TELEGRAM_BOT_TOKEN")
        if token and ":" in token:
            return token
        print("Token invalido. Debe contener ':'. Intentalo de nuevo.\n")


def step_user_id() -> str:
    print()
    print("— Paso 2: Tu ID de Telegram —")
    print()
    print("Solo tu podras usar el bot. Necesitas tu user ID numerico:")
    print("  1. Abre Telegram y busca @userinfobot")
    print("  2. Enviale cualquier mensaje")
    print("  3. Te respondera con tu ID numerico")
    print()
    while True:
        uid = ask("Tu AUTHORIZED_USER_ID")
        if uid.isdigit():
            return uid
        print("Debe ser un numero. Intentalo de nuevo.\n")


def step_projects_dir() -> str:
    default = str(Path.home() / "ClaudeProjects")
    print()
    print("— Paso 3: Directorio de proyectos —")
    print()
    print("Carpeta donde Claude Code buscara tus proyectos.")
    print("Deja vacio para usar el valor por defecto.")
    print()
    path = ask("CLAUDE_PROJECTS_DIR", default)
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def step_check_claude():
    print()
    print("— Paso 4: Verificar Claude Code CLI —")
    print()
    if shutil.which("claude"):
        print("claude CLI encontrado en PATH.")
    else:
        print("AVISO: 'claude' no se encontro en PATH.")
        print("El bot necesita Claude Code CLI instalado.")
        print("Instalalo con: npm install -g @anthropic-ai/claude-code")
        print()
        resp = ask("Continuar de todos modos? (s/n)", "s")
        if resp.lower() not in ("s", "si", "y", "yes"):
            print("Instalacion cancelada.")
            sys.exit(1)


def step_venv():
    print()
    print("— Paso 5: Entorno virtual y dependencias —")
    print()
    venv_dir = PROJECT_DIR / "venv"
    if venv_dir.exists():
        print("venv ya existe, saltando creacion.")
    else:
        print("Creando entorno virtual...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("venv creado.")

    # Determinar pip segun el SO
    if sys.platform == "win32":
        pip = str(venv_dir / "Scripts" / "pip.exe")
    else:
        pip = str(venv_dir / "bin" / "pip")

    print("Instalando dependencias...")
    subprocess.run([pip, "install", "-r", str(PROJECT_DIR / "requirements.txt")], check=True)
    print("Dependencias instaladas.")


def step_write_env(token: str, user_id: str, projects_dir: str):
    print()
    print("— Paso 6: Generar .env —")
    print()
    env_path = PROJECT_DIR / ".env"

    if env_path.exists():
        resp = ask("Ya existe .env. Sobreescribir? (s/n)", "n")
        if resp.lower() not in ("s", "si", "y", "yes"):
            print("Se conserva el .env existente.")
            return

    default_projects = str(Path.home() / "ClaudeProjects")
    lines = [
        f"TELEGRAM_BOT_TOKEN={token}",
        f"AUTHORIZED_USER_ID={user_id}",
    ]
    # Solo escribir si el usuario cambio el default
    if projects_dir != default_projects:
        lines.append(f"CLAUDE_PROJECTS_DIR={projects_dir}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f".env generado en {env_path}")


def step_autostart():
    if sys.platform != "win32":
        print()
        print("Auto-arranque solo disponible en Windows. Saltando.")
        return

    print()
    print("— Paso 7: Auto-arranque con Windows —")
    print()
    resp = ask("Quieres que el bot inicie automaticamente al encender Windows? (s/n)", "n")
    if resp.lower() not in ("s", "si", "y", "yes"):
        print("Saltado. Puedes ejecutarlo manualmente con start_bot.bat")
        return

    ps_script = PROJECT_DIR / "create_shortcut.ps1"
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
        check=True,
    )
    print("Shortcut de inicio creado.")


def main():
    banner()

    token = step_token()
    user_id = step_user_id()
    projects_dir = step_projects_dir()
    step_check_claude()
    step_venv()
    step_write_env(token, user_id, projects_dir)
    step_autostart()

    print()
    print("=" * 50)
    print("  Instalacion completada!")
    print("=" * 50)
    print()
    print("Para iniciar el bot:")
    print(f"  start_bot.bat        (con auto-restart)")
    print(f"  venv\\Scripts\\python -m bot.main  (directo)")
    print()
    print("Comandos basicos: /start, /help, /projects")
    print("Multi-bot: /spawn, /bots, /kill, /addtoken")
    print()
    print("Para crear workers necesitas tokens adicionales")
    print("de @BotFather y anadirlos con /addtoken en Telegram.")
    print()


if __name__ == "__main__":
    main()
