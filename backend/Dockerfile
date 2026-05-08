FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && cp /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /build

COPY . /build/

RUN cd /build && uv pip install --system --no-cache .

FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED="true" \
    PYTHONPATH="." \
    HF_HOME="/home/appuser/.cache/huggingface"

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . /app/

RUN useradd -r -s /bin/false appuser && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser

RUN chmod +x /app/run.sh

USER appuser

EXPOSE 8000

CMD ["/app/run.sh"]
