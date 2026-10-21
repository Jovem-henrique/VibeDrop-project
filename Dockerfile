FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Deno é recomendado pelo yt-dlp para desafios JavaScript do YouTube.
ENV DENO_INSTALL=/opt/deno
RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="/opt/deno/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .
# Mantém a versão estável fixada em requirements.txt para reproduzir o comportamento anterior.
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import importlib.metadata; print('VibeDrop yt-dlp:', importlib.metadata.version('yt-dlp'))"
COPY . .

ENV PORT=10000
EXPOSE 10000
# Mantenha 1 worker: a fila de trabalhos fica na memória desse processo.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120 app:app"]
