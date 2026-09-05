# EchoVault — Portable Windows .exe

Turn your existing EchoVault codebase into a single, install-free
`EchoVault.exe` for Windows. **No changes are made to your app code** — this
adds two files and one build step.

## Files to add to your project
Place both in the project root (next to `wsgi.py`, `requirements.txt`, `app\`):

| File | Purpose |
|------|---------|
| `desktop_launcher.py` | The exe's entry point. Imports your unchanged `create_app()` and adapts it for standalone Windows (waitress server, media streaming without Nginx, bundled FFmpeg, portable paths). |
| `build_windows_exe.bat` | Run this to produce `dist\EchoVault.exe`. |

## How to build (on Windows)
1. Copy `desktop_launcher.py` and `build_windows_exe.bat` into the
   `echovault-homelab-audio-main` folder.
2. Double-click **`build_windows_exe.bat`** (or run it from a terminal).
3. Wait for it to finish. Your file appears at **`dist\EchoVault.exe`**.

> A Windows .exe must be built on Windows — PyInstaller does not cross-compile.
> The script needs Python 3.10+ and internet access the first time (to fetch
> PyInstaller, waitress and a static FFmpeg build).

## How to use the exe
- Double-click **`EchoVault.exe`** — no installation.
- A console window opens and your browser goes to `http://127.0.0.1:8080`.
- Sign in with **admin / change-me-now** (change it — see below).
- Your **library and database** are saved in an `EchoVault-Data` folder created
  next to the exe, so they persist between runs and the exe stays portable
  (copy the exe + that folder to any Windows PC).
- Close the console window to stop the server.

## What the build script does
1. Creates an isolated `.buildenv` virtual environment.
2. Installs your `requirements.txt` plus `waitress` and `pyinstaller`.
3. Downloads a static **FFmpeg** build once into `ffmpeg_bin\` (needed by
   yt-dlp to produce the 192 kbps MP3).
4. Runs PyInstaller in `--onefile` mode, bundling:
   - your `app\templates` and `app\static`,
   - `ffmpeg.exe` + `ffprobe.exe`,
   - the full `yt_dlp` package (all extractors).
5. Emits `dist\EchoVault.exe`.

## Why a launcher was needed (not just "PyInstaller wsgi.py")
Your app targets Docker + Gunicorn + Nginx, none of which exist in a portable
exe. `desktop_launcher.py` bridges that **without editing your code**:

- **Server:** gunicorn can't run on Windows → serves via **waitress**.
- **Media:** `routes.py` streams audio by setting an `X-Accel-Redirect` header
  that only Nginx honours. The launcher intercepts that header and streams the
  file itself, **with HTTP range support** so seeking works.
- **FFmpeg:** bundled inside the exe and added to `PATH` for yt-dlp.
- **Paths:** Linux `/media` and `/data` are remapped to the portable
  `EchoVault-Data` folder beside the exe.

## Change the admin password
Set an environment variable before launching (e.g. create a small
`start.bat` next to the exe):
```bat
set ADMIN_PASSWORD=your-strong-password
set ECHOVAULT_PORT=8080
EchoVault.exe
```
Or change it in the app after first sign-in once you add that feature.

## Notes & expectations
- The exe will be **~90–150 MB** (FFmpeg + yt-dlp). That's normal for a
  self-contained, no-install bundle.
- Keep **yt-dlp** fresh: rebuild periodically (`pip install -U yt-dlp` happens
  automatically via `requirements.txt` if you bump the pin) — YouTube changes
  break older versions.
- Windows SmartScreen may warn on first run of an unsigned exe (Right-click →
  Properties → Unblock, or "More info → Run anyway"). Code-signing removes this
  but requires a certificate.
- Reminder from your own README: only import media you own or are authorized to
  download.
