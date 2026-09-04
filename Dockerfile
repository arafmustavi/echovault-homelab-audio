FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/echovault
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY wsgi.py .
ENV PYTHONUNBUFFERED=1
# FIX: single worker so the in-memory `jobs` dict and the background download
# threads live in ONE process. With multiple workers the /api/job poller can hit
# a different worker than the one that created the job -> "Job not found".
# Threads keep concurrency for playback/streaming. Move jobs to Redis/RQ if you
# later need to scale to multiple workers.
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:8000", "--timeout", "600", "wsgi:app"]
