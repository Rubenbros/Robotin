# Claude Telegram Bot

Bot privado de Telegram que conecta con [Claude Code](https://docs.anthropic.com/en/docs/claude-code) para interactuar con tus proyectos desde el movil.

## Que hace

- Envia texto y recibe respuestas de Claude Code
- Envia imagenes para que Claude las analice
- Envia notas de voz (transcripcion con Whisper + respuesta de Claude)
- Gestiona multiples proyectos con sesiones persistentes
- Genera imagenes con Gemini via skill dedicada
- Botones interactivos nativos de Telegram
- Auto-arranque en Windows

## Requisitos previos

- **Python 3.11+**
- **Claude Code CLI** instalado y en PATH (`npm install -g @anthropic-ai/claude-code`)
- **Token de bot de Telegram** (obtenido de [@BotFather](https://t.me/BotFather))
- **Tu Telegram User ID** (obtenido de [@userinfobot](https://t.me/userinfobot))

## Instalacion rapida

```bash
git clone https://github.com/tu-usuario/claude-telegram-bot.git
cd claude-telegram-bot
python setup.py
```

El instalador interactivo te guiara paso a paso: token, user ID, directorio de proyectos, dependencias y auto-arranque opcional.

## Instalacion manual

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu token y user ID
python -m bot.main
```

## Comandos del bot

| Comando | Descripcion |
|---------|-------------|
| `/start` | Bienvenida e info del bot |
| `/help` | Lista completa de comandos |
| `/projects` | Proyectos disponibles (botones) |
| `/select <nombre>` | Seleccionar proyecto |
| `/nochat` | Volver a chat libre (sin proyecto) |
| `/newproject <nombre>` | Crear proyecto nuevo |
| `/status` | Estado de proyecto y sesion |
| `/clear` / `/newchat` | Limpiar sesion actual |
| `/stop` | Detener ejecucion en curso |
| `/gemini [rapido\|pro] [clean] <prompt>` | Generar imagen con Gemini |

## Configuracion

Variables de entorno (`.env`):

| Variable | Descripcion | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token de BotFather | (requerido) |
| `AUTHORIZED_USER_ID` | Tu ID numerico de Telegram | (requerido) |
| `CLAUDE_PROJECTS_DIR` | Carpeta de proyectos | `~/ClaudeProjects` |
| `CLAUDE_SKILLS_DIR` | Carpeta de skills de Claude | `~/.claude/skills` |

## Auto-arranque en Windows

El instalador puede configurar auto-arranque. Si prefieres hacerlo manualmente:

```powershell
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

Esto crea un acceso directo en la carpeta Startup de Windows que ejecuta el bot en segundo plano al iniciar sesion.

## Estructura del proyecto

```
claude-telegram-bot/
├── bot/
│   ├── config.py              # Configuracion central
│   ├── main.py                # Entry point
│   ├── security.py            # Autorizacion
│   ├── handlers/              # Comandos y mensajes
│   └── services/              # Claude, Whisper, sesiones
├── data/                      # Sesiones y archivos temporales
├── setup.py                   # Instalador interactivo
├── start_bot.bat              # Launcher con auto-restart
├── start_bot_hidden.vbs       # Launcher en segundo plano
├── create_shortcut.ps1        # Crear acceso directo Startup
├── requirements.txt
└── .env.example
```

## Licencia

Uso personal.
