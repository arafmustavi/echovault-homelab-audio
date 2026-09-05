"""
desktop_launcher.py — portable Windows entry point for EchoVault
================================================================
This is the file PyInstaller turns into EchoVault.exe. It does NOT modify the
existing app: it imports the unchanged `create_app()` and adapts the runtime so
the app can run as a single, install-free Windows executable.

What it bridges (all things Docker/Nginx/Gunicorn normally provide):
  1. Server      -> serves with waitress (gunicorn does not run on Windows).
  2. Media files -> your routes.py sets an `X-Accel-Redirect` header expecting
                    Nginx to stream the file. There is no Nginx here, so we
                    intercept that header and stream the file ourselves, with
                    HTTP range support so seeking in the <audio> player works.
  3. FFmpeg      -> yt-dlp needs ffmpeg to make the 192 kbps MP3. We add the
                    ffmpeg folder bundled inside the exe to PATH.
  4. Paths       -> Linux /media and /data are remapped to folders created
                    right next to EchoVault.exe, so the app is portable and
                    keeps your library + database between runs.

Nothing in ./app is edited. This file is standalone and additive.
"""
from __future__ import annotations
import os
import sys
import secrets
import socket
import threading
import webbrowser
from pathlib import Path

PORT = int(os.environ.get("ECHOVAULT_PORT", "8080"))
HOST = "127.0.0.1"


# --------------------------------------------------------------------------- #
# Paths — work both when frozen (exe) and when run as a plain script.
# --------------------------------------------------------------------------- #
def app_base_dir() -> Path:
    """Folder the user sees the exe in (persistent data lives here)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """Folder PyInstaller unpacks bundled data/binaries into at runtime."""
    return Path(getattr(sys, "_MEIPASS", str(app_base_dir())))


BASE = app_base_dir()
DATA = BASE / "EchoVault-Data"
MEDIA = DATA / "media"
INSTANCE = DATA / "instance"
for d in (MEDIA, INSTANCE):
    d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Persist a stable SECRET_KEY so logins/CSRF survive restarts.
# --------------------------------------------------------------------------- #
_secret_file = DATA / "secret.key"
if _secret_file.exists():
    _secret = _secret_file.read_text(encoding="utf-8").strip()
else:
    _secret = secrets.token_hex(32)
    _secret_file.write_text(_secret, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Environment the unchanged app reads in create_app(). Set BEFORE importing app.
# --------------------------------------------------------------------------- #
_db_path = str((INSTANCE / "echovault.db").resolve()).replace("\\", "/")
os.environ.setdefault("MEDIA_ROOT", str(MEDIA))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("SECRET_KEY", _secret)
os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "change-me-now")
os.environ.setdefault("ALLOW_REGISTRATION", "true")

# Put the bundled ffmpeg on PATH so yt-dlp can find ffmpeg.exe / ffprobe.exe.
_ffmpeg_dir = bundle_dir() / "ffmpeg"
if _ffmpeg_dir.exists():
    os.environ["PATH"] = str(_ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")


# --------------------------------------------------------------------------- #
# Build the app (unchanged) and add the Nginx-less media streamer.
# --------------------------------------------------------------------------- #
from flask import send_file, abort            # noqa: E402
from app import create_app                     # noqa: E402  (your existing package)

app = create_app()


@app.after_request
def _stream_media_without_nginx(response):
    """Turn the app's `X-Accel-Redirect` into a real file stream.

    routes.py builds an empty Response carrying
        X-Accel-Redirect: /protected-media/<filename>
    which only Nginx would honour. Here we detect that header and instead send
    the actual file from MEDIA_ROOT, with conditional=True enabling HTTP range
    requests (so seeking/scrubbing the audio works).
    """
    accel = response.headers.get("X-Accel-Redirect", "")
    prefix = "/protected-media/"
    if accel.startswith(prefix):
        rel = accel[len(prefix):]
        # Guard against path traversal; media filenames are flat basenames.
        if ".." in rel or rel.startswith(("/", "\\")):
            abort(404)
        full = (MEDIA / rel).resolve()
        try:
            full.relative_to(MEDIA.resolve())
        except ValueError:
            abort(404)
        if not full.exists():
            abort(404)
        return send_file(str(full), mimetype="audio/mpeg", conditional=True)
    return response


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    port = PORT
    if not _port_free(HOST, port):
        # try a few alternatives before giving up
        for alt in range(port + 1, port + 11):
            if _port_free(HOST, alt):
                port = alt
                break

    print("=" * 60)
    print("  EchoVault — portable edition")
    print(f"  Open:      http://{HOST}:{port}")
    print(f"  Admin ID:  {os.environ['ADMIN_USER']}")
    print(f"  Password:  {os.environ['ADMIN_PASSWORD']}  (change this!)")
    print(f"  Library:   {MEDIA}")
    print(f"  Database:  {INSTANCE / 'echovault.db'}")
    print("  Close this window to stop the server.")
    print("=" * 60)

    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{port}")).start()

    from waitress import serve
    serve(app, host=HOST, port=port, threads=8, channel_timeout=600)


if __name__ == "__main__":
    main()
