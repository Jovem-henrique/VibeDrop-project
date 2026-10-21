FROM python:3.14.8-slim

ARG YTDLP_SOURCE_COMMIT=f59cd0ba0a3c666fa5d8793b073fa9f03cfecc22
ENV YTDLP_SOURCE_COMMIT=${YTDLP_SOURCE_COMMIT}

# Instala FFmpeg 9.0.2 (build Linux x86_64) e Deno 2.9.8 de fontes fixadas e valida seus SHA-256.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl unzip xz-utils; \
    mkdir -p /tmp/ffmpeg-extract /tmp/deno-extract; \
    curl --fail --show-error --location --retry 3 \
      --output /tmp/ffmpeg.tar.xz \
      "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-21-13-06/ffmpeg-n9.0.2-31-gc89d6ee1ca-linux64-gpl-9.0.tar.xz"; \
    echo "2212009529e7a18809c0a23700e8045364c17853c4390cf8c051e6b65dd97bde  /tmp/ffmpeg.tar.xz" | sha256sum -c -; \
    tar --wildcards -xJf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg-extract '*/bin/ffmpeg' '*/bin/ffprobe'; \
    install -m 0755 /tmp/ffmpeg-extract/*/bin/ffmpeg /usr/local/bin/ffmpeg; \
    install -m 0755 /tmp/ffmpeg-extract/*/bin/ffprobe /usr/local/bin/ffprobe; \
    curl --fail --show-error --location --retry 3 \
      --output /tmp/deno.zip \
      "https://github.com/denoland/deno/releases/download/v2.9.8/deno-x86_64-unknown-linux-gnu.zip"; \
    echo "e890975bc2549807bbcc0b584ffafda72cc7c93349dd99c80483dd784f6c4609  /tmp/deno.zip" | sha256sum -c -; \
    unzip -q /tmp/deno.zip -d /tmp/deno-extract; \
    install -m 0755 /tmp/deno-extract/deno /usr/local/bin/deno; \
    ffmpeg -version | head -n 1; \
    ffprobe -version | head -n 1; \
    deno --version; \
    rm -rf /tmp/ffmpeg-extract /tmp/deno-extract /tmp/ffmpeg.tar.xz /tmp/deno.zip; \
    apt-get purge -y --auto-remove curl unzip xz-utils; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN set -eux; \
    python -m pip install --no-cache-dir --upgrade pip; \
    python -m pip install --no-cache-dir -r requirements.txt; \
    python --version; \
    python -m pip --version; \
    python -c "import importlib.metadata, platform; print('VibeDrop Python:', platform.python_version()); print('VibeDrop Flask:', importlib.metadata.version('Flask')); print('VibeDrop yt-dlp:', importlib.metadata.version('yt-dlp')); print('VibeDrop yt-dlp source commit: f59cd0ba0a3c666fa5d8793b073fa9f03cfecc22'); print('VibeDrop Gunicorn:', importlib.metadata.version('gunicorn'))"; \
    ffmpeg -version | head -n 1; \
    ffprobe -version | head -n 1; \
    deno --version
COPY . .

ENV PORT=10000
EXPOSE 10000
# Mantenha 1 worker: a fila de trabalhos fica na memória desse processo.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120 app:app"]
