@echo off
echo ==========================================================
echo       AI Voice Interview Agent Container Verification     
echo ==========================================================
echo.

echo [1/4] Checking running container statuses...
docker compose ps
echo.

echo [2/4] Checking database healthcheck status...
docker inspect --format="{{json .State.Health.Status}}" interview-agent-db 2>nul
if errorlevel 1 echo PostgreSQL DB container not found.
echo.

echo [3/4] Testing FastAPI Backend connection ^& health endpoint...
curl -s -f http://localhost:8000/health >nul
if %errorlevel% equ 0 (
    echo Backend: OK (Healthy)
    curl -s http://localhost:8000/health
) else (
    echo Backend: ERROR (Port 8000 is not responding)
)
echo.
echo.

echo [4/4] Testing Ollama and pre-downloaded model status...
curl -s -f http://localhost:11434/api/tags >nul
if %errorlevel% equ 0 (
    echo Ollama: OK (Responding)
    echo Downloaded Models:
    curl -s http://localhost:11434/api/tags
) else (
    echo Ollama: ERROR (Port 11434 is not responding)
)
echo.
echo.

echo === Verification script completed ===
pause
