FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/echovault
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY wsgi.py .
ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:8000", "--timeout", "600", "wsgi:app"]
