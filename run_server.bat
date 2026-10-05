@echo off
REM ============================================================================
REM  P0 -- Python inference service (FastAPI)
REM
REM  Port is 8001, NOT 8000: on this machine 8000 and 7000 are blocked by the
REM  system (WinError 10013). 8001/8002/5001/3000/5173 all tested OK.
REM  Also deliberately avoids 8080 (Spring Boot) and 5173 (Vite) so they
REM  never collide later.
REM
REM  NOTE: comments are ASCII only on purpose -- Chinese here would be
REM  garbled in the default console codepage.
REM
REM  WARNING: must run from the PROJECT ROOT, because app.py uses
REM  "from ai import ..." which requires the "ai" package to be importable.
REM ============================================================================

set "PORT=8001"

cd /d D:\vegetable_fruit_yolo

echo ============================================================
echo   Persimmon ripeness service - Python inference
echo ============================================================
echo.
echo   After start (first run takes ~15s to preload models),
echo   open in your browser:
echo.
echo      http://127.0.0.1:%PORT%/        test page (drag an image in)
echo      http://127.0.0.1:%PORT%/docs    auto-generated API docs
echo.
echo   Phone on the same WiFi works too -- replace 127.0.0.1
echo   with this machine's LAN IP.
echo   Close this window to stop the service.
echo ============================================================
echo.

D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port %PORT%

echo.
echo ------------------------------------------------------------
echo   service exited, errorlevel = %ERRORLEVEL%
echo.
echo   If you see WinError 10013, that port is blocked by the system;
echo   change PORT=8001 to 8002 or 5001.
echo.
echo   If you see ModuleNotFoundError: No module named 'fastapi',
echo   the venv is missing packages:
echo       pip install fastapi uvicorn python-multipart
echo ------------------------------------------------------------
pause
