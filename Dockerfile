# ───────────────────────── Dockerfile (round-1B) ─────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# I/O dirs
RUN mkdir -p /app/input /app/output

# Python deps
COPY requirements.txt .

# ① CPU-only Torch
RUN pip install --no-cache-dir torch==2.2.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# ② everything else (now includes rank_bm25)
RUN pip install --no-cache-dir -r requirements.txt

# ③ cache MiniLM
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
print("✓ Cached embedding model")
PY

# code & assets
COPY assets/fonts /app/fonts
COPY app/        /app/app
COPY main.py     /app/main.py
COPY persona_job.json /app/persona_job.json

ENTRYPOINT ["python", "main.py"]
# ───────────────────────────────────────────────────────────────────────────