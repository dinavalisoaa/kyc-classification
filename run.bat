@echo off
setlocal
cd /d "%~dp0"

if not exist venv (
    echo [setup] creation venv...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [setup] installation dependances...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo [run] demarrage serveur Flask (chargement modele, patienter)...
start "serveur-flask" /min cmd /c "python app.py"

:wait
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:5000 > "%TEMP%\flask_check.txt" 2>nul
set /p CODE=<"%TEMP%\flask_check.txt"
if not "%CODE%"=="200" (
    echo [run] serveur pas encore pret...
    goto wait
)

echo [run] serveur pret, ouverture navigateur.
start "" http://127.0.0.1:5000

endlocal
