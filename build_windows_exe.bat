@echo off
REM ===================================================================
REM  build_windows_exe.bat  —  EchoVault portable Windows .exe builder
REM  -------------------------------------------------------------------
REM  Run this ON WINDOWS from inside the echovault-homelab-audio-main
REM  folder (the one containing wsgi.py, app\, requirements.txt and the
REM  desktop_launcher.py you dropped in).
REM
REM  Output:  dist\EchoVault.exe   (single, portable, no install needed)
REM
REM  Requires: Python 3.10+ on PATH and an internet connection (to fetch
REM  PyInstaller, waitress and a static FFmpeg build once).
REM  NOTE: PyInstaller is not a cross-compiler — a Windows .exe must be
REM  built on Windows. This script does exactly that.
REM ===================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo [1/6] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
  echo   ERROR: Python 3.10+ was not found on PATH.
  echo   Install it from https://www.python.org/downloads/ and re-run.
  exit /b 1
)

if not exist "desktop_launcher.py" (
  echo   ERROR: desktop_launcher.py not found in this folder.
  echo   Place it next to wsgi.py, then re-run this script.
  exit /b 1
)

echo.
echo [2/6] Creating build virtual environment (.buildenv)...
if not exist ".buildenv" python -m venv .buildenv
call ".buildenv\Scripts\activate.bat"

echo.
echo [3/6] Installing dependencies (app + waitress + PyInstaller)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 ( echo   ERROR: failed installing requirements.txt & exit /b 1 )
pip install waitress pyinstaller
if errorlevel 1 ( echo   ERROR: failed installing waitress/pyinstaller & exit /b 1 )

echo.
echo [4/6] Fetching a static FFmpeg build (one-time)...
if exist "ffmpeg_bin\ffmpeg.exe" (
  echo   FFmpeg already present, skipping download.
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$u='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';" ^
    "Write-Host '   downloading' $u;" ^
    "Invoke-WebRequest -Uri $u -OutFile 'ffmpeg.zip';" ^
    "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg_tmp' -Force;" ^
    "$exe=Get-ChildItem 'ffmpeg_tmp' -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1;" ^
    "$probe=Get-ChildItem 'ffmpeg_tmp' -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1;" ^
    "New-Item -ItemType Directory -Force 'ffmpeg_bin' | Out-Null;" ^
    "Copy-Item $exe.FullName 'ffmpeg_bin\ffmpeg.exe' -Force;" ^
    "Copy-Item $probe.FullName 'ffmpeg_bin\ffprobe.exe' -Force;" ^
    "Remove-Item 'ffmpeg.zip','ffmpeg_tmp' -Recurse -Force"
  if errorlevel 1 ( echo   ERROR: FFmpeg download/extract failed. & exit /b 1 )
)

echo.
echo [5/6] Building EchoVault.exe with PyInstaller...
pyinstaller --noconfirm --clean --onefile --name EchoVault ^
  --add-data "app\templates;app\templates" ^
  --add-data "app\static;app\static" ^
  --add-binary "ffmpeg_bin\ffmpeg.exe;ffmpeg" ^
  --add-binary "ffmpeg_bin\ffprobe.exe;ffmpeg" ^
  --collect-all yt_dlp ^
  --collect-all mutagen ^
  --hidden-import waitress ^
  --hidden-import sqlalchemy.dialects.sqlite ^
  desktop_launcher.py
if errorlevel 1 ( echo   ERROR: PyInstaller build failed. & exit /b 1 )

echo.
echo [6/6] Done.
echo ============================================================
echo   Portable executable:  dist\EchoVault.exe
echo   Just double-click it (no install). It opens your browser
echo   at http://127.0.0.1:8080 and stores your library + database
echo   in an "EchoVault-Data" folder next to the exe.
echo ============================================================
echo.
pause
endlocal
