# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Set timezone so the scheduler reads PST correctly
ENV TZ=America/Los_Angeles
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files ────────────────────────────────────────────────────────
COPY . .

# ── Create logs directory ─────────────────────────────────────────────────────
RUN mkdir -p logs

# ── Run the bot ───────────────────────────────────────────────────────────────
CMD ["python", "main.py"]
