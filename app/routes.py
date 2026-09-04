import os, re, threading, uuid
from pathlib import Path
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from mutagen import File as MutagenFile
from . import db
from .models import User, Track, Playlist

ALLOWED = {'mp3', 'm4a', 'aac', 'ogg', 'opus', 'wav', 'flac', 'webm'}

# In-memory job store. NOTE: this only works when Gunicorn runs a SINGLE worker
# (see Dockerfile: --workers 1 --threads 8). With >1 worker the download thread
# and the /api/job poller land in different processes and you get "Job not found".
# For multi-worker scaling, move this to Redis/RQ (see README roadmap).
jobs = {}


def safe_name(name):
    return secure_filename(name)[:160] or str(uuid.uuid4())


def duration_of(path):
    try:
        a = MutagenFile(path)
        return int(a.info.length) if a and a.info else 0
    except Exception:
        return 0


def download_job(app, job_id, url, user_id, media_root):
    """Background import worker.

    FIX: receives the Flask `app` object explicitly and pushes ONE app context
    for all DB writes, instead of relying on `current_app` / a leaked context
    from the caller. `user_id` is resolved in the request thread and passed in,
    so we never touch the request-bound `current_user` proxy from here.
    """
    jobs[job_id] = {'status': 'downloading', 'message': 'Fetching media and metadata'}
    try:
        import yt_dlp
        out = str(Path(media_root) / '%(title).140s-%(id)s.%(ext)s')
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': out,
            'noplaylist': False,
            'ignoreerrors': False,
            'writethumbnail': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail'},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
            ],
            'quiet': True,
            'restrictfilenames': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get('entries') if isinstance(info, dict) else None
            entries = [x for x in entries if x] if entries else [info]

            imported = 0
            with app.app_context():
                for x in entries:
                    prepared = Path(ydl.prepare_filename(x))
                    audio = prepared.with_suffix('.mp3')
                    if not audio.exists():
                        matches = list(Path(media_root).glob(f"*{x.get('id', '')}*.mp3"))
                        audio = matches[0] if matches else None
                    if audio and audio.exists():
                        if not Track.query.filter_by(filename=audio.name).first():
                            t = Track(
                                title=x.get('title') or audio.stem,
                                artist=x.get('artist') or x.get('uploader') or 'Unknown Artist',
                                album=x.get('album') or 'Imported',
                                filename=audio.name,
                                source_url=url,
                                duration=int(x.get('duration') or 0),
                                added_by=user_id,
                            )
                            db.session.add(t)
                            db.session.commit()
                            imported += 1

        if imported:
            jobs[job_id] = {'status': 'complete', 'message': f'Imported {imported} track(s)'}
        else:
            # Download finished but nothing usable was produced — usually a
            # yt-dlp/FFmpeg extraction issue rather than a silent success.
            jobs[job_id] = {'status': 'failed',
                            'message': 'No audio track was produced. Check yt-dlp is up to date and FFmpeg is installed.'}
    except Exception as e:
        jobs[job_id] = {'status': 'failed', 'message': str(e)[:300]}


def register_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            u = User.query.filter_by(username=request.form.get('username', '').strip()).first()
            if u and u.check_password(request.form.get('password', '')):
                login_user(u)
                return redirect(url_for('home'))
            flash('Invalid user ID or password.', 'error')
        return render_template('auth.html', mode='login')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if not app.config['ALLOW_REGISTRATION']:
            return ('Registration disabled', 403)
        if request.method == 'POST':
            name = request.form.get('username', '').strip()
            pwd = request.form.get('password', '')
            if not re.fullmatch(r'[A-Za-z0-9_.-]{3,30}', name):
                flash('Use 3-30 letters, numbers, dots, dashes or underscores.', 'error')
            elif len(pwd) < 8:
                flash('Password must contain at least 8 characters.', 'error')
            elif User.query.filter_by(username=name).first():
                flash('That user ID already exists.', 'error')
            else:
                u = User(username=name)
                u.set_password(pwd)
                db.session.add(u)
                db.session.commit()
                login_user(u)
                return redirect(url_for('home'))
        return render_template('auth.html', mode='register')

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def home():
        q = request.args.get('q', '').strip()
        query = Track.query
        if q:
            query = query.filter(db.or_(
                Track.title.ilike(f'%{q}%'),
                Track.artist.ilike(f'%{q}%'),
                Track.album.ilike(f'%{q}%')))
        return render_template(
            'index.html',
            tracks=query.order_by(Track.created_at.desc()).all(),
            playlists=Playlist.query.filter_by(owner_id=current_user.id).all(),
            q=q)

    @app.route('/add', methods=['GET', 'POST'])
    @login_required
    def add():
        if request.method == 'POST':
            url = request.form.get('url', '').strip()
            f = request.files.get('file')
            if url:
                if not url.startswith(('http://', 'https://')):
                    flash('Enter a valid HTTP or HTTPS URL.', 'error')
                else:
                    # FIX: resolve the user HERE (inside the request context) and
                    # hand the app + uid to the thread. Never read current_user
                    # from inside the background thread.
                    uid = current_user.id
                    jid = str(uuid.uuid4())
                    jobs[jid] = {'status': 'queued', 'message': 'Waiting to start'}
                    threading.Thread(
                        target=download_job,
                        args=(app, jid, url, uid, app.config['MEDIA_ROOT']),
                        daemon=True).start()
                    return redirect(url_for('job', job_id=jid))
            elif f and '.' in f.filename and f.filename.rsplit('.', 1)[1].lower() in ALLOWED:
                name = f'{uuid.uuid4().hex[:8]}-{safe_name(f.filename)}'
                path = Path(app.config['MEDIA_ROOT']) / name
                f.save(path)
                t = Track(title=Path(f.filename).stem, filename=name,
                          duration=duration_of(path), added_by=current_user.id)
                db.session.add(t)
                db.session.commit()
                flash('Audio uploaded.', 'success')
                return redirect(url_for('home'))
            else:
                flash('Paste a supported link or choose an audio file.', 'error')
        return render_template('add.html')

    @app.route('/job/<job_id>')
    @login_required
    def job(job_id):
        return render_template('job.html', job_id=job_id)

    @app.route('/api/job/<job_id>')
    @login_required
    def job_api(job_id):
        return jsonify(jobs.get(job_id, {'status': 'unknown', 'message': 'Job not found'}))

    @app.route('/media/<path:filename>')
    @login_required
    def media(filename):
        track = Track.query.filter_by(filename=filename).first_or_404()
        response = Response()
        response.headers['X-Accel-Redirect'] = f'/protected-media/{track.filename}'
        response.headers['Content-Type'] = 'audio/mpeg'
        response.headers['Content-Disposition'] = f'inline; filename="{track.filename}"'
        return response

    @app.route('/api/tracks/<int:tid>/play', methods=['POST'])
    @login_required
    def play(tid):
        t = db.get_or_404(Track, tid)
        t.plays += 1
        db.session.commit()
        return jsonify(ok=True, plays=t.plays)

    @app.route('/playlist', methods=['POST'])
    @login_required
    def playlist():
        n = request.form.get('name', '').strip()[:100]
        if n:
            db.session.add(Playlist(name=n, owner_id=current_user.id))
            db.session.commit()
        return redirect(url_for('home'))

    @app.route('/playlist/<int:pid>/add/<int:tid>', methods=['POST'])
    @login_required
    def playlist_add(pid, tid):
        p = Playlist.query.filter_by(id=pid, owner_id=current_user.id).first_or_404()
        t = db.get_or_404(Track, tid)
        if t not in p.tracks:
            p.tracks.append(t)
            db.session.commit()
        return redirect(url_for('home'))
