@echo off
REM ============================================================================
REM  Open the camera and run two-layer recognition in real time.
REM    layer 1  detect   models\persimmon_det_v1\best.pt
REM    layer 2  classify models\persimmon_cls_v1\best.pt
REM
REM  To use another camera, change the last "0" to 1.
REM
REM  NOTE: comments in this file are ASCII only on purpose.
REM  Writing Chinese here would be garbled in the default console codepage.
REM
REM  WARNING: must run from the PROJECT ROOT, because detect.py uses
REM  "from ai import ..." which requires the "ai" package to be importable.
REM ============================================================================

cd /d D:\vegetable_fruit_yolo

D:\Anaconda\envs\yolo\python.exe -m ai.detect 0

echo.
echo ------------------------------------------------------------
echo   camera exited, errorlevel = %ERRORLEVEL%
echo   0 = normal close, non-zero = crashed on start (see error above)
echo ------------------------------------------------------------
pause
