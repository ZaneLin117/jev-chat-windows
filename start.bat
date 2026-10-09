@echo off
setlocal
cd /d "%~dp0" || goto :fail

if not exist ".venv312\Scripts\python.exe" (
    echo Python 3.12 environment not found: .venv312
    echo Create .venv312 with Python 3.12 and install requirements.txt first.
    goto :fail
)

".venv312\Scripts\python.exe" main.py
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo Jev Chat could not start. See the error above.
pause
exit /b 1
