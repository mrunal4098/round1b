# ─────────────────────────── Dockerfile  (round-1B) ───────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ── OS deps ────────────────────────────────────────────────────────────────
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# ── create I/O dirs (judge will bind-mount over them) ──────────────────────
RUN mkdir -p /app/input /app/output

# ── Python deps ────────────────────────────────────────────────────────────
COPY requirements.txt .

# 1) install CPU-only Torch FIRST (must use the extra index URL)
RUN pip install --no-cache-dir torch==2.2.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# 2) install the rest of your requirements
RUN pip install --no-cache-dir -r requirements.txt

# 3) pre-download the embedding model so container works offline
ARG MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RUN python - <<'PY'
import os
from sentence_transformers import SentenceTransformer
model_name = os.environ.get("MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
SentenceTransformer(model_name)          # downloads & caches inside image
print(f"✓ Cached {model_name}")
PY

# ── copy code & assets ─────────────────────────────────────────────────────
COPY assets/fonts /app/fonts
COPY app/ /app/app

ENTRYPOINT ["python", "-m", "app.main"]
# ───────────────────────────────────────────────────────────────────────────