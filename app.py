"""VibeDrop 2.1 — áudio e vídeo para links individuais públicos/autorizados.

Flask + yt-dlp + FFmpeg. Use um worker Gunicorn: fila em memória.
O aplicativo não contorna DRM, login, conteúdo privado nem restrições de plataformas.
"""
from __future__ import annotations

import hmac
import importlib.metadata
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yt_dlp
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('PUBLIC_HTTPS', '0') == '1',
    MAX_CONTENT_LENGTH=4096,
)
ACCESS_CODE = os.getenv('APP_ACCESS_CODE', '').strip()
if os.getenv('PUBLIC_HTTPS') == '1' and not ACCESS_CODE:
    raise RuntimeError('Defina APP_ACCESS_CODE antes de expor o VibeDrop na internet.')

app.logger.info('VibeDrop iniciado; yt-dlp=%s', importlib.metadata.version('yt-dlp'))

VIDEO_ID = re.compile(r'^[a-zA-Z0-9_-]{11}$')
IG_ID = re.compile(r'^[a-zA-Z0-9_-]{5,40}$')
TIKTOK_ID = re.compile(r'^\d{6,30}$')
TIKTOK_USER = re.compile(r'^@[a-zA-Z0-9._]{1,32}$')
TIKTOK_SHORT = re.compile(r'^[a-zA-Z0-9_-]{4,80}$')
VIDEO_QUALITIES = {'best', '1080', '720', '480', '360'}
SUPPORTED_FORMATS = {'mp3', 'm4a', 'mp4'}

# Sem duração máxima e sem teto fixo de MB por padrão. Mínimo de espaço livre
# protege o computador contra discos lotados; ajuste conforme o hardware.
MIN_FREE_GB = float(os.getenv('MIN_FREE_GB', '2'))
MAX_FILE_MB = int(os.getenv('MAX_FILE_MB', '0'))  # zero = sem teto fixo
if MIN_FREE_GB < 0 or MAX_FILE_MB < 0:
    raise ValueError('MIN_FREE_GB e MAX_FILE_MB não podem ser negativos.')
MIN_FREE_BYTES = int(MIN_FREE_GB * 1024 ** 3)
MAX_FILE_BYTES = MAX_FILE_MB * 1024 ** 2
MAX_SIMULTANEOUS = max(1, min(2, int(os.getenv('MAX_SIMULTANEOUS', '2'))))
TTL_SECONDS = max(5, int(os.getenv('RESULT_TTL_MINUTES', '30'))) * 60
# Limite global de conversões/hora removido; intervalo por sessão após terminar.
CLIENT_COOLDOWN_SECONDS = max(0, int(os.getenv('CLIENT_COOLDOWN_SECONDS', '60')))
PREVIEW_HOURLY_LIMIT = max(1, int(os.getenv('PREVIEW_HOURLY_LIMIT', '30')))

executor = ThreadPoolExecutor(max_workers=MAX_SIMULTANEOUS)
lock = threading.Lock()
jobs: dict[str, Job] = {}
client_cooldowns: dict[str, float] = {}
previews: list[float] = []
login_attempts: dict[str, list[float]] = {}


@dataclass
class Job:
    id: str
    url: str
    fmt: str
    folder: Path
    created: float
    quality: str = 'best'
    platform: str = ''
    status: str = 'queued'
    message: str = 'Aguardando...'
    percent: int = 0
    filename: str = ''
    file_path: Path | None = None
    ended: float | None = None
    client_id: str = ''


def normalize_media_link(raw_url: str) -> tuple[str, str]:
    """Aceita apenas formatos conhecidos de permalink em domínios oficiais.

    Não entregue URLs arbitrárias ao yt-dlp: extrações alcançam outros hosts.
    A lista reduz o risco de SSRF, mas não substitui isolamento de rede.
    """
    if not isinstance(raw_url, str) or not 12 <= len(raw_url) <= 500:
        raise ValueError('Cole um link de vídeo válido.')
    try:
        p = urlsplit(raw_url.strip())
        port = p.port
    except ValueError as exc:
        raise ValueError('Link inválido.') from exc
    if p.scheme != 'https' or p.username or p.password or port is not None or p.fragment:
        raise ValueError('Use um link HTTPS público e direto, sem porta ou credenciais.')
    host = (p.hostname or '').lower()
    if not host or p.path.startswith('//') or '%' in p.path or '\\' in p.path:
        raise ValueError('Link inválido ou não suportado.')
    parts = p.path.strip('/').split('/')

    if host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be', 'www.youtu.be'):
        vid = None
        if host in ('youtu.be', 'www.youtu.be'):
            if len(parts) == 1:
                vid = parts[0]
        elif p.path == '/watch':
            vid = parse_qs(p.query).get('v', [None])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'live'):
            vid = parts[1]
        if not vid or not VIDEO_ID.fullmatch(vid):
            raise ValueError('YouTube: use o link de um vídeo individual ou Short.')
        return f'https://www.youtube.com/watch?v={vid}', 'YouTube'

    if host in ('instagram.com', 'www.instagram.com'):
        if len(parts) == 2 and parts[0] in ('p', 'reel', 'tv') and IG_ID.fullmatch(parts[1]):
            return f'https://www.instagram.com/{parts[0]}/{parts[1]}/', 'Instagram'
        raise ValueError('Instagram: use um link público de publicação ou Reel.')

    if host in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com'):
        if len(parts) == 3 and TIKTOK_USER.fullmatch(parts[0]) and parts[1] == 'video' and TIKTOK_ID.fullmatch(parts[2]):
            return f'https://www.tiktok.com/{parts[0]}/video/{parts[2]}', 'TikTok'
        # Alguns links de compartilhamento são curtos, sem dados do autor.
        if len(parts) == 2 and parts[0] == 't' and TIKTOK_SHORT.fullmatch(parts[1]):
            return f'https://www.tiktok.com/t/{parts[1]}/', 'TikTok'
        raise ValueError('TikTok: use um link público de vídeo individual.')
    if host in ('vm.tiktok.com', 'vt.tiktok.com'):
        if len(parts) == 1 and TIKTOK_SHORT.fullmatch(parts[0]):
            return f'https://{host}/{parts[0]}/', 'TikTok'
        raise ValueError('TikTok: link de compartilhamento inválido.')

    raise ValueError('Aceitamos links individuais públicos do YouTube, Instagram e TikTok.')


def safe_thumbnail(raw: object) -> str | None:
    """Somente CDNs conhecidos, evitando requisições do browser para hosts privados."""
    if not isinstance(raw, str) or len(raw) > 1000:
        return None
    try:
        p = urlsplit(raw)
        host = (p.hostname or '').lower()
        port = p.port
    except ValueError:
        return None
    trusted = ('ytimg.com', 'cdninstagram.com', 'fbcdn.net', 'tiktokcdn.com',
               'tiktokcdn-us.com', 'tiktokv.com', 'byteimg.com')
    if p.scheme != 'https' or port is not None or p.username or p.password:
        return None
    if not any(host == root or host.endswith('.' + root) for root in trusted):
        return None
    return raw


def clean_filename(name: str) -> str:
    name = re.sub(r'[\\/\x00-\x1f\x7f<>:"|?*]+', ' ', name or 'arquivo')
    name = re.sub(r'\s+', ' ', name).strip(' .')
    return name[:110] or 'arquivo'


def check_free_space(path: Path) -> None:
    if shutil.disk_usage(path).free < MIN_FREE_BYTES:
        raise RuntimeError('Espaço insuficiente no servidor. Aguarde ou avise o administrador.')


def cleanup_expired() -> None:
    now = time.time()
    old_dirs: list[Path] = []
    with lock:
        for jid, job in list(jobs.items()):
            if job.ended is not None and now - job.ended > TTL_SECONDS:
                old_dirs.append(job.folder)
                jobs.pop(jid, None)
        for client_id, until in list(client_cooldowns.items()):
            if until <= now:
                client_cooldowns.pop(client_id, None)
        previews[:] = [x for x in previews if now - x < 3600]
        for ip, times in list(login_attempts.items()):
            times[:] = [x for x in times if now - x < 60]
            if not times:
                del login_attempts[ip]
    for folder in old_dirs:
        shutil.rmtree(folder, ignore_errors=True)


def cleanup_loop() -> None:
    while True:
        time.sleep(60)
        cleanup_expired()


threading.Thread(target=cleanup_loop, daemon=True).start()


def update_job(job: Job, **changes: object) -> None:
    with lock:
        for key, value in changes.items():
            setattr(job, key, value)
        if 'ended' in changes and changes['ended'] is not None and job.client_id:
            client_cooldowns[job.client_id] = float(changes['ended']) + CLIENT_COOLDOWN_SECONDS


def media_options(job: Job, progress) -> dict:
    options = {
        'outtmpl': str(job.folder / 'media.%(ext)s'),
        'noplaylist': True,
        'ignoreerrors': False,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'retries': 2,
        'fragment_retries': 2,
        'progress_hooks': [progress],
        'match_filter': lambda info, *, incomplete=False: (
            'Transmissões ao vivo não são permitidas.'
            if info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming')
            else None
        ),
    }
    if MAX_FILE_BYTES:
        options['max_filesize'] = MAX_FILE_BYTES

    if job.fmt == 'mp3':
        options['format'] = 'bestaudio/best'
        options['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
    elif job.fmt == 'm4a':
        options['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
        options['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}]
    else:
        cap = '' if job.quality == 'best' else f'[height<={int(job.quality)}]'
        # Tenta primeiro MP4 + áudio M4A, depois outros codecs convertíveis.
        options['format'] = (
            f'bestvideo[ext=mp4]{cap}+bestaudio[ext=m4a]/'
            f'best[ext=mp4]{cap}/'
            f'bestvideo{cap}+bestaudio/'
            f'best{cap}'
        )
        options['merge_output_format'] = 'mp4'
        # Se o único arquivo disponível for WEBM, converte o contêiner para MP4.
        options['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
    return options


def friendly_download_error(platform: str, error: Exception | str) -> str:
    """Converte erros técnicos conhecidos em mensagens úteis sem expor detalhes internos."""
    error_text = str(error).lower()
    platform_name = platform.lower()

    if (
        'espaço insuficiente' in error_text
        or 'no space left' in error_text
        or 'disk quota exceeded' in error_text
    ):
        return 'Espaço insuficiente no servidor para processar esta mídia. Tente novamente mais tarde.'
    if 'limite de tamanho' in error_text or 'larger than max-filesize' in error_text:
        return 'O arquivo ultrapassou o limite de 370 MB configurado para este serviço.'
    if 'ffmpeg' in error_text or 'ffprobe' in error_text:
        return 'A ferramenta de conversão de mídia falhou no servidor. Tente novamente mais tarde.'
    if platform_name == 'instagram' and any(
        term in error_text for term in ('rate-limit', 'rate limit', 'login page', 'accessing posts anonymously')
    ):
        return (
            'O Instagram limitou o acesso anônimo deste servidor. Isso não é causado pelo limite de tamanho. '
            'Aguarde e tente novamente mais tarde com outra publicação pública autorizada. '
            'O VibeDrop não utiliza cookies de contas pessoais para contornar esse bloqueio.'
        )
    if platform_name == 'youtube' and any(
        term in error_text for term in ('failed to extract any player response', 'unable to extract initial player response')
    ):
        return (
            'O YouTube não forneceu ao servidor a resposta necessária para localizar esta mídia. '
            'A plataforma pode ter mudado ou restringido o acesso do servidor. Tente novamente mais tarde '
            'ou teste outro vídeo público autorizado.'
        )
    if 'rate-limit' in error_text or 'rate limit' in error_text:
        return f'{platform} limitou temporariamente os acessos deste servidor. Aguarde e tente novamente mais tarde.'
    if 'sign in' in error_text or 'not a bot' in error_text or '403' in error_text or 'login page' in error_text:
        return f'{platform} restringiu este acesso. Tente novamente mais tarde ou use outro link público autorizado.'
    return (
        'Não foi possível baixar esta mídia. A plataforma pode ter restringido o acesso, '
        'ou o link/formato pode estar indisponível. Tente outro link público autorizado.'
    )


def download_job(job: Job) -> None:
    def progress(details: dict) -> None:
        if details.get('status') == 'downloading':
            downloaded = details.get('downloaded_bytes') or 0
            total = details.get('total_bytes') or details.get('total_bytes_estimate') or 0
            if MAX_FILE_BYTES and (downloaded > MAX_FILE_BYTES or (total and total > MAX_FILE_BYTES)):
                raise yt_dlp.utils.DownloadError('Limite de tamanho de arquivo atingido.')
            check_free_space(job.folder)
            percent = min(89, round(downloaded / total * 89)) if total else 10
            update_job(job, status='working', percent=percent, message='Baixando mídia...')
        elif details.get('status') == 'finished':
            update_job(job, status='working', percent=92, message='Convertendo / finalizando arquivo...')

    try:
        check_free_space(job.folder)
        update_job(job, status='working', percent=3, message='Verificando mídia...')
        with yt_dlp.YoutubeDL(media_options(job, progress)) as ydl:
            info = ydl.extract_info(job.url, download=True)
        if not isinstance(info, dict):
            raise RuntimeError('Mídia indisponível para download.')
        options = list(job.folder.glob(f'media.{job.fmt}'))
        if not options:
            options = [p for p in job.folder.glob(f'*.{job.fmt}') if p.is_file()]
        if not options:
            raise RuntimeError('O formato solicitado não pôde ser gerado.')
        output = options[0]
        if MAX_FILE_BYTES and output.stat().st_size > MAX_FILE_BYTES:
            raise RuntimeError('Limite de tamanho de arquivo atingido.')
        filename = f"{clean_filename(info.get('title') or 'mídia')}.{job.fmt}"
        update_job(job, status='ready', percent=100, message='Pronto para baixar!', filename=filename,
                   file_path=output, ended=time.time())
    except Exception as exc:
        msg = friendly_download_error(job.platform, exc)
        app.logger.warning('Trabalho %s não concluído: %s', job.id, exc)
        update_job(job, status='error', percent=0, message=msg, ended=time.time())
        shutil.rmtree(job.folder, ignore_errors=True)


@app.before_request
def require_access_code():
    if request.endpoint in ('health', 'login', 'static'):
        return None
    if not ACCESS_CODE:
        session.setdefault('client_id', secrets.token_urlsafe(18))
        return None
    if session.get('access_granted') is True:
        session.setdefault('client_id', secrets.token_urlsafe(18))
        return None
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Sessão expirada. Faça login novamente.'}), 401
    return redirect(url_for('login'))


@app.after_request
def secure_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not ACCESS_CODE:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        # Limite simples de tentativas de senha por IP (melhorar via Redis na nuvem).
        key = request.remote_addr or 'unknown'
        now = time.time()
        with lock:
            recent = [x for x in login_attempts.get(key, []) if now - x < 60]
            if len(recent) >= 8:
                return render_template('login.html', error='Muitas tentativas. Aguarde um minuto.'), 429
            recent.append(now)
            login_attempts[key] = recent
        if hmac.compare_digest(request.form.get('code', ''), ACCESS_CODE):
            session.clear()
            session['access_granted'] = True
            session['client_id'] = secrets.token_urlsafe(18)
            return redirect(url_for('index'))
        error = 'Código incorreto. Tente novamente.'
    return render_template('login.html', error=error)


@app.get('/')
def index():
    return render_template('index.html')


@app.post('/api/preview')
def preview():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Informe um link.'}), 400
    try:
        target, platform = normalize_media_link(payload.get('url'))
    except (ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    now = time.time()
    with lock:
        previews[:] = [x for x in previews if now - x < 3600]
        if len(previews) >= PREVIEW_HOURLY_LIMIT:
            return jsonify({'error': 'Muitas prévias solicitadas. Tente mais tarde.'}), 429
        previews.append(now)
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'noplaylist': True,
                                'skip_download': True, 'socket_timeout': 15,
                                'retries': 1, 'extract_flat': False}) as ydl:
            info = ydl.extract_info(target, download=False)
        if not isinstance(info, dict) or info.get('is_live'):
            raise RuntimeError('Prévia indisponível')
        return jsonify({
            'title': str(info.get('title') or 'Mídia sem título')[:160],
            'platform': platform,
            'duration': info.get('duration') if isinstance(info.get('duration'), (int, float)) else None,
            # Exibimos apenas miniaturas hospedadas em HTTPS.
            'thumbnail': safe_thumbnail(info.get('thumbnail')),
        })
    except Exception:
        return jsonify({'error': 'Não conseguimos carregar a prévia; tente o download diretamente.'}), 422


@app.post('/api/jobs')
def submit_job():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Informe um link e um formato.'}), 400
    fmt = payload.get('format')
    quality = str(payload.get('quality', 'best'))
    if fmt not in SUPPORTED_FORMATS:
        return jsonify({'error': 'Escolha MP3, M4A ou MP4.'}), 400
    if fmt == 'mp4' and quality not in VIDEO_QUALITIES:
        return jsonify({'error': 'Qualidade de vídeo inválida.'}), 400
    if fmt != 'mp4':
        quality = 'best'
    try:
        url, platform = normalize_media_link(payload.get('url'))
    except (ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    cleanup_expired()
    now = time.time()
    client_id = session['client_id']
    with lock:
        if any(j.client_id == client_id and j.status in ('queued', 'working') for j in jobs.values()):
            return jsonify({'error': 'Você já tem uma conversão em andamento.'}), 429
        wait = client_cooldowns.get(client_id, 0) - now
        if wait > 0:
            return jsonify({'error': f'Aguarde {int(wait) + 1} segundos antes de outra conversão.'}), 429
        active = sum(j.status in ('queued', 'working') for j in jobs.values())
        if active >= MAX_SIMULTANEOUS:
            return jsonify({'error': 'O servidor está ocupado. Tente novamente em instantes.'}), 429
        jid = secrets.token_urlsafe(20)
        folder = Path(tempfile.mkdtemp(prefix='vibedrop_'))
        job = Job(jid, url, fmt, folder, now, quality=quality, platform=platform, client_id=client_id)
        jobs[jid] = job
    executor.submit(download_job, job)
    return jsonify({'job_id': job.id}), 202


@app.get('/api/jobs/<job_id>')
def job_status(job_id: str):
    cleanup_expired()
    with lock:
        job = jobs.get(job_id)
        if job is None or job.client_id != session['client_id']:
            return jsonify({'error': 'Download não encontrado ou expirado.'}), 404
        return jsonify({
            'status': job.status, 'message': job.message, 'percent': job.percent,
            'filename': job.filename if job.status == 'ready' else None,
            'download_url': url_for('download_result', job_id=job_id) if job.status == 'ready' else None,
        })


@app.get('/api/jobs/<job_id>/download')
def download_result(job_id: str):
    cleanup_expired()
    with lock:
        job = jobs.get(job_id)
        if job is None or job.client_id != session['client_id'] or job.status != 'ready' or not job.file_path:
            return jsonify({'error': 'Arquivo indisponível ou expirado.'}), 404
        path, name = job.file_path, job.filename
    if not path.is_file():
        return jsonify({'error': 'Arquivo não encontrado.'}), 404
    mime = {'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'mp4': 'video/mp4'}[job.fmt]
    return send_file(path, as_attachment=True, download_name=name, mimetype=mime)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '8000')), debug=False)
