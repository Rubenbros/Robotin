@echo off
title Claude Telegram Bot
cd /d %~dp0

:loop
echo [%date% %time%] Iniciando bot...
venv\Scripts\python.exe -m bot.main
echo [%date% %time%] Bot detenido (codigo: %errorlevel%). Reiniciando en 5 segundos...
timeout /t 5 /nobreak >nul
goto loop
