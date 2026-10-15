FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    EASYOCR_MODULE_PATH=/app/.EasyOCR \
    USE_TF=0 \
    USE_FLAX=0 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Install a compatible CPU pair first so dependency resolution does not pull
# CUDA libraries onto a CPU-only host.
RUN pip install --no-cache-dir torch==2.8.0+cpu torchvision==0.23.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && pip check

COPY app ./app
COPY data ./data
COPY scripts/prepare_runtime.py ./scripts/prepare_runtime.py

# Bake public model weights and the bundled policy index into the image.
# Each preparation stage runs separately to release model memory between stages.
# No provider credentials are needed or copied into this build.
RUN python -m scripts.prepare_runtime

# Requests use the prepared cache instead of downloading models at runtime.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
