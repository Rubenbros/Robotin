# Claude Telegram Bot

Bot privado de Telegram que conecta con [Claude Code](https://docs.anthropic.com/en/docs/claude-code) para interactuar con tus proyectos desde el movil.

## Que hace

- Envia texto y recibe respuestas de Claude Code
- Envia imagenes para que Claude las analice
- Envia notas de voz (transcripcion con Whisper + respuesta de Claude)
- Gestiona multiples proyectos con sesiones persistentes
- Sistema multi-bot: crea workers dedicados por proyecto y rol
- Genera imagenes con Gemini via skill dedicada
- Botones interactivos nativos de Telegram
- Menu de comandos nativo con autocompletado
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

### Proyectos

| Comando | Descripcion |
|---------|-------------|
| `/projects` | Proyectos disponibles (botones) |
| `/select <nombre>` | Seleccionar proyecto |
| `/newproject <nombre>` | Crear proyecto nuevo |
| `/nochat` | Volver a chat libre (sin proyecto) |
| `/status` | Estado de proyecto y sesion |

### Sesion

| Comando | Descripcion |
|---------|-------------|
| `/clear` / `/newchat` | Limpiar sesion actual |
| `/stop` | Detener ejecucion en curso |

### Herramientas

| Comando | Descripcion |
|---------|-------------|
| `/ask <pregunta>` | Pregunta rapida sin sesion |
| `/devbot` | Trabajar en el propio bot |
| `/gemini [rapido\|pro] [clean] <prompt>` | Generar imagen con Gemini |

### Multi-bot (workers)

| Comando | Descripcion |
|---------|-------------|
| `/spawn [rol]` | Crear worker dedicado a un proyecto |
| `/bots` | Ver workers activos |
| `/kill [nombre]` | Detener un worker |
| `/stopall` | Detener todos los workers |
| `/addtoken <token>` | Agregar token de bot al pool |
| `/removetoken <id>` | Quitar token del pool |

Los workers son bots independientes dedicados a un proyecto y rol especifico. Cada worker tiene su propia sesion persistente (por proyecto+rol), que se conserva al reiniciar.

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
│   ├── main.py                # Entry point (coordinador)
│   ├── worker_main.py         # Entry point (workers)
│   ├── security.py            # Autorizacion
│   ├── handlers/
│   │   ├── commands.py        # Comandos generales
│   │   ├── coordinator_commands.py  # Comandos multi-bot
│   │   ├── worker_commands.py       # Comandos del worker
│   │   ├── text_handler.py    # Mensajes de texto
│   │   ├── image_handler.py   # Imagenes
│   │   ├── voice_handler.py   # Notas de voz
│   │   └── callback_handler.py  # Botones inline
│   └── services/
│       ├── claude_service.py  # Comunicacion con Claude Code
│       ├── session_manager.py # Sesiones persistentes
│       ├── token_pool.py      # Pool de tokens de bot
│       ├── worker_registry.py # Registro de workers
│       └── project_manager.py # Gestion de proyectos
├── data/                      # Sesiones y estado
├── setup.py                   # Instalador interactivo
├── start_bot.bat              # Launcher con auto-restart
├── watchdog.vbs               # Watchdog en segundo plano
├── create_shortcut.ps1        # Acceso directo Startup
├── requirements.txt
└── .env.example
```

## Licencia

Uso personal.
