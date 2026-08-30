# EchoVault

A polished, self-hosted Flask audio library for a personal homelab. EchoVault supports user ID/password accounts, audio uploads, link-based imports, playlists, search, play counts, responsive playback, Docker, and an Nginx reverse proxy.

## Important use policy
Only download or store media you own, that is public domain, or that you have explicit permission to copy. You are responsible for platform terms, copyright, and local law. EchoVault does not bypass DRM.

## Quick start with Docker
1. Install Docker Desktop (Windows/macOS) or Docker Engine + Compose (Linux).
2. Unzip this folder.
3. Copy `.env.example` to `.env`.
4. Change `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`.
5. From the project folder run:

```bash
docker compose up --build -d
```

6. Open `http://localhost:8080`.
7. Sign in with the admin credentials from `.env`, or create a user account.

Stop with:

```bash
docker compose down
```

Your database stays in `./instance`; media stays in `./media`.

## Homelab deployment
- Put the project on your server/NAS-backed path.
- Mount your large storage into the app and Nginx containers by changing `./media:/media` in both services.
- Keep port 8000 internal. Expose only Nginx.
- For internet access, use HTTPS at your existing reverse proxy and forward to `http://HOMELAB_IP:8080`.
- Do not expose the application with the default secret or password.
- Consider disabling public signup with `ALLOW_REGISTRATION=false` after creating users.

## Link imports
EchoVault uses yt-dlp plus FFmpeg, included in the Docker image. Paste a supported, authorized URL in **Add music**. Imports run in a lightweight background thread and convert audio to 192 kbps MP3. Playlists from supported sources can import multiple tracks.

## Included features
- User ID/password registration and login
- Secure password hashing and CSRF protection
- Admin bootstrap account
- Search by title, artist, or album
- Authenticated browser audio playback through an internal Nginx media location, including range support
- Audio file uploads up to 500 MB
- Authorized video/audio/playlist URL ingestion
- Metadata extraction and embedded thumbnails where supported
- User-owned playlists
- Play counters
- Dark, responsive Spotify/Apple Music-inspired interface
- Docker Compose persistence

## Recommended next roadmap
1. Replace in-memory jobs with Redis + Celery/RQ.
2. Add admin approval, invitation codes, quotas, and password reset.
3. Add album artwork extraction and WebP caching.
4. Add favorites, queue persistence, listening history, and smart playlists.
5. Add Meilisearch/OpenSearch, recommendations, and audio fingerprint duplicate detection.
6. Add Prometheus/Grafana health metrics and scheduled backups.
7. Add a PWA manifest and offline playlist sync.
8. Add OIDC/passkeys and rate limiting before wider exposure.

## Local Python mode (without Docker)
Requires Python 3.12+ and FFmpeg on PATH. Create `/data` and `/media`, or adjust `.env` paths. Install requirements, export variables, then run `flask --app wsgi run`. Docker is the recommended path.

## Security notes
This is a portfolio-quality MVP, not a completed public SaaS. Before exposing to the internet, add TLS, rate limits, account lockout, security headers, backups, monitoring, and a durable job queue. Keep yt-dlp patched because supported sites change frequently.
