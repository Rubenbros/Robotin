@echo off
title Claude Telegram Bot
cd /d %~dp0

if not exist logs mkdir logs

:loop
echo [%date% %time%] Iniciando bot...
echo [%date% %time%] Iniciando bot... >> logs\bot.log
venv\Scripts\python.exe -m bot.main 2>> logs\bot_error.log
set exitcode=%errorlevel%
echo [%date% %time%] Bot detenido (codigo: %exitcode%). Reiniciando en 5 segundos...
echo [%date% %time%] Bot detenido (codigo: %exitcode%). Reiniciando en 5 segundos... >> logs\bot.log
timeout /t 5 /nobreak >nul
goto loop
