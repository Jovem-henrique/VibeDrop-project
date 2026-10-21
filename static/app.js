const form = document.getElementById('convert-form');
const urlInput = document.getElementById('video-url');
const submitButton = document.getElementById('submit-btn');
const buttonLabel = document.getElementById('button-label');
const statusBox = document.getElementById('job-status');
const message = document.getElementById('job-message');
const percentage = document.getElementById('job-percent');
const progress = document.getElementById('job-progress');
const link = document.getElementById('download-link');
const errorBox = document.getElementById('error-box');
const audioTab = document.getElementById('audio-tab');
const videoTab = document.getElementById('video-tab');
const audioSettings = document.getElementById('audio-settings');
const videoSettings = document.getElementById('video-settings');
const quality = document.getElementById('quality');
const previewButton = document.getElementById('preview-btn');
const mediaPreview = document.getElementById('media-preview');
const previewImage = document.getElementById('preview-image');
let mode = 'audio';
let isBusy = false;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const showError = text => { errorBox.textContent = text; errorBox.hidden = false; };
const hideError = () => { errorBox.textContent = ''; errorBox.hidden = true; };
const setBusy = state => {
  isBusy = state;
  submitButton.disabled = state;
  buttonLabel.textContent = state ? 'Processando sua mídia...' : (mode === 'video' ? 'Baixar vídeo MP4' : 'Converter áudio');
};
const readJson = async response => {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Erro do servidor (${response.status}).`);
  return data;
};
const selectMode = next => {
  if (isBusy) return;
  mode = next;
  const audio = mode === 'audio';
  audioTab.classList.toggle('active', audio);
  videoTab.classList.toggle('active', !audio);
  audioTab.setAttribute('aria-pressed', String(audio));
  videoTab.setAttribute('aria-pressed', String(!audio));
  audioSettings.hidden = !audio;
  videoSettings.hidden = audio;
  buttonLabel.textContent = audio ? 'Converter áudio' : 'Baixar vídeo MP4';
};
audioTab.addEventListener('click', () => selectMode('audio'));
videoTab.addEventListener('click', () => selectMode('video'));
document.querySelectorAll('.format-option input').forEach(input => {
  input.addEventListener('change', () => {
    document.querySelectorAll('.format-option').forEach(label => label.classList.toggle('selected', label.querySelector('input').checked));
  });
});
document.getElementById('paste-btn').addEventListener('click', async () => {
  try { urlInput.value = await navigator.clipboard.readText(); mediaPreview.hidden = true; urlInput.focus(); }
  catch (_) { urlInput.focus(); showError('Cole o link manualmente; a área de transferência não foi autorizada.'); }
});
urlInput.addEventListener('input', () => { mediaPreview.hidden = true; });
previewButton.addEventListener('click', async () => {
  hideError();
  mediaPreview.hidden = true;
  if (!urlInput.value.trim()) { showError('Cole o link para ver a prévia.'); return; }
  previewButton.disabled = true;
  previewButton.textContent = 'Carregando prévia...';
  try {
    const info = await readJson(await fetch('/api/preview', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({url: urlInput.value.trim()})
    }));
    document.getElementById('preview-title').textContent = info.title;
    document.getElementById('preview-platform').textContent = info.platform;
    const seconds = Number(info.duration);
    document.getElementById('preview-duration').textContent =
      Number.isFinite(seconds) && seconds > 0 ? `Duração: ${Math.floor(seconds/3600) ? `${Math.floor(seconds/3600)}h ` : ''}${Math.floor(seconds%3600/60)}min ${Math.floor(seconds%60)}s` : 'Duração não informada';
    // Thumbnail nunca é inserida como HTML; vem de URLs HTTPS da plataforma.
    previewImage.hidden = !info.thumbnail;
    if (info.thumbnail) previewImage.src = info.thumbnail;
    mediaPreview.hidden = false;
  } catch (err) { showError(err.message || 'Não foi possível carregar a prévia.'); }
  finally { previewButton.disabled = false; previewButton.textContent = '✧ Ver prévia do link'; }
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (isBusy) return;
  hideError(); statusBox.hidden = true; link.hidden = true;
  const url = urlInput.value.trim();
  if (!url) { showError('Cole o link de um vídeo primeiro.'); urlInput.focus(); return; }
  const format = mode === 'video' ? 'mp4' : form.querySelector('input[name="format"]:checked').value;
  const requestedQuality = mode === 'video' ? quality.value : 'best';
  setBusy(true);
  try {
    const {job_id} = await readJson(await fetch('/api/jobs', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({url, format, quality: requestedQuality}),
    }));
    statusBox.hidden = false;
    message.textContent = 'Seu pedido entrou na fila...';
    percentage.textContent = '0%'; progress.style.width = '0%';
    let networkFailures = 0;
    // Sem timeout arbitrário de seis minutos: vídeos longos podem demorar.
    while (true) {
      await sleep(1500);
      let result;
      try {
        result = await readJson(await fetch(`/api/jobs/${encodeURIComponent(job_id)}`, {cache:'no-store'}));
        networkFailures = 0;
      } catch (err) {
        if (++networkFailures <= 4) continue;
        throw err;
      }
      message.textContent = result.message;
      percentage.textContent = `${result.percent}%`;
      progress.style.width = `${result.percent}%`;
      if (result.status === 'ready') {
        link.href = result.download_url;
        link.hidden = false;
        link.setAttribute('download', result.filename || `media.${format}`);
        return;
      }
      if (result.status === 'error') throw new Error(result.message);
    }
  } catch (err) {
    showError(err.message || 'Não foi possível concluir o pedido.');
  } finally { setBusy(false); }
});
