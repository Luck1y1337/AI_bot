FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the database (and long_term.json, stored alongside it) under /data.
# Mount a Railway Volume at /data in the dashboard so it survives redeploys.
ENV DB_PATH=/data/mahiro.db

CMD ["python", "main.py"]
