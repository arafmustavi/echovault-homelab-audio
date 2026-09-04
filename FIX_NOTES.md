# EchoVault — YouTube import fix

## Symptom
Adding a link never imports the track. The job page shows **"Unknown / Job not found"**
(see the phone screenshot at `192.168.1.13:8080`).

## Root causes

### 1. Multi-worker + in-memory job store  ← the "Job not found" you saw
- `app/routes.py` stores job status in a module-level dict: `jobs = {}`.
- `Dockerfile` ran Gunicorn with `--workers 2`.
- The POST `/add` request is served by one worker (which owns the job + the
  download thread). The browser then polls `GET /api/job/<id>`, which Gunicorn
  may route to the **other** worker, whose `jobs` dict doesn't contain the id.
- Result: `jobs.get(job_id, {'status':'unknown','message':'Job not found'})`
  returns exactly the card in the screenshot.

### 2. Background thread reads request-bound state
- The thread was launched with:
  `lambda: app.app_context().push() or download_job(jid,url,current_user.id,...)`
- `current_user.id` is evaluated **inside the thread**, where there is no request
  context, so `current_user` is the anonymous user and `.id` raises
  `AttributeError`. The thread dies before `download_job` runs.
- Pushing an app context inside a throwaway lambda also leaks the context.

## Fixes applied

### Dockerfile
```
- CMD ["gunicorn", "--workers", "2", "--threads", "4", ...]
+ CMD ["gunicorn", "--workers", "1", "--threads", "8", ...]
```
One process => the `jobs` dict and background threads are always consistent.

### app/routes.py
- `download_job(app, job_id, url, user_id, media_root)` now takes the `app`
  object and does all DB writes inside a single `with app.app_context():`.
- In `/add`, the user id is captured in the request (`uid = current_user.id`)
  and passed to the thread via `args=(app, jid, url, uid, media_root)` — no more
  reading `current_user` from the worker thread.
- If yt-dlp finishes but produces no `.mp3`, the job is now marked **failed**
  with a helpful message instead of silently reporting success.

## How to apply
1. Replace `echovault/Dockerfile` with the provided `Dockerfile`.
2. Replace `echovault/app/routes.py` with the provided `routes.py`.
3. Rebuild and restart:
   ```
   docker compose down
   docker compose up --build -d
   ```
4. Open http://<homelab-ip>:8080 -> Add music -> paste an authorized URL.

## If a specific URL still fails
The code path is now correct, so any remaining failure will show a real error
message on the job page (not "Job not found"). The usual culprit is yt-dlp
falling behind YouTube changes. Bump it and rebuild:
```
# requirements.txt
yt-dlp>=2026.8.19      # or pin to the latest release
```
FFmpeg is already in the image, which yt-dlp needs for the MP3 postprocessing.

> Reminder: import only media you own or are authorized to download — per your
> own README's use policy.
