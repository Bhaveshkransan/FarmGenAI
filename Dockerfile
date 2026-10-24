# Stage 1: Build virtual environment dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies for C-extensions (asyncpg, psycopg2, numpy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# Pre-install CPU-only PyTorch so sentence-transformers does NOT pull 3+ GB of CUDA/NVIDIA packages
# Using --extra-index-url preserves PyPI for standard build tools (flit_core, etc.)
RUN pip install --no-cache-dir --user torch --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining application dependencies
RUN pip install --no-cache-dir --upgrade pip && pip install --default-timeout=1000 --retries 10 --no-cache-dir --user -r requirements.txt

# Stage 2: Production release environment
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH="/app"

# Install runtime dependencies:
# - libgomp1: required by XGBoost and scikit-learn for OpenMP threading
# - libpq5: PostgreSQL client runtime library
# - curl: container healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages and binaries from builder
COPY --from=builder /root/.local /root/.local
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
