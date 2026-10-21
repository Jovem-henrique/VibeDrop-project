# 🎵 VibeDrop 2.2

> Um projeto de portfólio em Python: uma interface web para obter cópias de **conteúdos públicos ou autorizados** em MP3, M4A e MP4, a partir de links individuais do YouTube, Instagram e TikTok.

**Status:** VibeDrop 2.2 — Render Free; acompanhe [PUBLICAR_RAILWAY.md](PUBLICAR_RAILWAY.md). A extração varia conforme plataforma, disponibilidade, direitos de uso e mudanças externas. A presença de uma plataforma na interface **não garante** que todo link funcionará.

## Runtime publicado — atualização de 21/10/2026

- Python 3.14.8; Flask 3.1.3; Gunicorn 26.2.2.
- yt-dlp fixado ao commit upstream `f59cd0ba0a3c666fa5d8793b073fa9f03cfecc22`, que inclui uma correção recente de extração inicial do YouTube.
- FFmpeg 9.0.2 (build Linux x86_64) e Deno 2.9.8, com verificações SHA-256 durante o build.
- O Dockerfile imprime as versões utilizadas para que falhas de extração possam ser investigadas nos logs.
- Os testes automáticos simulam serviços externos; eles não garantem que o YouTube, Instagram ou TikTok permitam downloads reais a partir do IP da Render.


## ✨ Funcionalidades

- Interface escura responsiva, preservando a identidade visual da primeira versão.
- **Áudio:** MP3 ou M4A (qualidade depende da fonte).
- **Vídeo:** MP4, resolução automática ou até 1080p, 720p, 480p e 360p quando disponíveis.
- Links de vídeos individuais públicos do **YouTube, Instagram (Reels/publicações) e TikTok**; sem playlists, perfis ou vídeos privados.
- Prévia opcional de título, duração e miniatura; pode falhar sem impedir tentativa de download.
- Progresso assíncrono e download temporário com expiração em 30 minutos.
- **Sem limite fixo de duração**; na Render Free, teto configurado de **370 MB por arquivo**, sujeito aos recursos do servidor.
- Acesso por senha opcional local e obrigatório na configuração HTTPS pública.

## 🐧 Rodando no Fedora 44

Abra esta pasta no VS Code e execute no terminal:

```bash
sudo dnf install python3-pip ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:8000`. Para testar recursos do YouTube no `yt-dlp` recente, pode ser necessário instalar o Deno; consulte a [documentação oficial do yt-dlp](https://github.com/yt-dlp/yt-dlp#dependencies) e do [Deno](https://docs.deno.com/runtime/).

**Teste primeiro no Fedora:** uma amostra MP3, M4A e MP4 de cada plataforma, usando somente conteúdos com permissão. Vídeos privados, links restritos ou novas exigências de autenticação não são suportados.

## 🗂️ Estrutura

```text
VibeDrop_2_0/
├── app.py                 # Flask, segurança, fila e yt-dlp
├── templates/
│   ├── index.html         # Interface principal
│   └── login.html         # Acesso com senha
├── static/
│   ├── style.css          # Identidade visual
│   └── app.js             # Interações, prévia e progresso
├── tests/test_app.py      # Testes automáticos sem downloads reais
├── Dockerfile             # Publicação futura (processo web)
├── requirements.txt
├── .env.example           # Exemplos de configuração (sem senhas)
├── .gitignore
└── CHANGELOG.md
```

## 🔒 Configuração e segurança

Para testar com acesso pela internet, **não exponha o servidor Flask de desenvolvimento**. Depois de ativar o venv, configure as variáveis e inicie o Gunicorn:

```bash
read -rsp 'Senha para amigos: ' APP_ACCESS_CODE; echo
export APP_ACCESS_CODE
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export PUBLIC_HTTPS=1
export MIN_FREE_GB=2
# 0 = sem teto fixo de tamanho; protecao por espaco minimo continua ativa
export MAX_FILE_MB=0
gunicorn --workers 1 --threads 4 --bind 127.0.0.1:8000 app:app
```

**Não salve a senha em arquivos versionados nem publique o terminal com ela.** O projeto restringe domínios e tipos de URL para reduzir SSRF, mas isso não substitui firewall, isolamento de rede e revisão antes de um lançamento público.

Para testes com link temporário e Gunicorn já em execução, inicie em outro terminal:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Os dois terminais precisam ficar abertos, e o computador ligado. Ao terminar, `Ctrl+C` na aba `cloudflared` e depois na aba `gunicorn`.

### Limites técnicos que permanecem

- Não há restrição arbitrária de **duração**. Downloads muito longos continuam sujeitos à conexão, acesso e tempo de processamento.
- `MAX_FILE_MB=0` elimina o teto de tamanho por arquivo. `MIN_FREE_GB=2` interrompe downloads se houver pouco espaço disponível; não garante ausência de esgotamento de disco durante conversão pelo FFmpeg.
- Na Render Free, **1 trabalho simultâneo**. A cota global de 10 conversões/hora foi removida e cada sessão aguarda 60 segundos após concluir uma conversão.
- Prévia limitada a 30 pedidos por hora para evitar consultas externas excessivas.
- Arquivos gerados expiram 30 minutos depois de prontos. Não há armazenamento permanente ou retomada após reiniciar o servidor.
- Use somente **um worker Gunicorn**: a fila atual existe na memória de um processo.
- Hospedagens pequenas podem ficar sem espaço/disco/rede. Para acesso público de muitos usuários, precisaremos de fila externa, limites distribuídos, cotas e armazenamento isolado.

## ✅ Testes automáticos

```bash
python -m unittest discover -s tests -v
```

Testam URL, seleção de formato/resolução, acesso, prévia simulada, download simulado e mídia longa. **Não fazem requisições de vídeo reais.**

## 🧑‍💻 Salvar no GitHub como projeto de portfólio

1. Crie um repositório chamado `vibedrop` no seu perfil do GitHub (pode começar privado).
2. No terminal, na raiz desta pasta:

   ```bash
   git init
   git add .
   git commit -m "feat: VibeDrop 2.0 com áudio e vídeo multiplataforma"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/vibedrop.git
   git push -u origin main
   ```

3. Substitua `SEU_USUARIO` pelo seu nome de usuário no GitHub. Nunca versione `.venv/`, `.env`, senhas, mídias baixadas ou arquivos temporários.
4. Após testes e revisão de segurança, decida se quer tornar o repositório público e publicar o site em hospedagem permanente.

## 🧰 Tecnologias e aprendizados

- **Python + Flask** — rotas REST, autenticação e servidor web.
- **yt-dlp + FFmpeg** — extração autorizada e tratamento de formatos de mídia.
- **HTML, CSS e JavaScript** — interface responsiva, formulários e requisições assíncronas.
- **Git/GitHub + testes** — versionamento, documentação e manutenção.

Esse repositório documenta uma evolução incremental: script no terminal → conversor web → VibeDrop 2.0. Pode ser apresentado como estudo prático de desenvolvimento web, integrações e organização de software.

## ⚖️ Uso responsável

Use só mídias próprias, em domínio público ou cuja cópia/download esteja autorizado. Respeite os direitos autorais, os termos das plataformas e as restrições técnicas aplicáveis. O projeto não promete acessar vídeos privados, protegidos ou bloqueados por plataformas.

## 🌐 Hospedagem permanente

As instruções para hospedar na Railway, configurar segredos, limites reais e publicar no GitHub estão em [PUBLICAR_RAILWAY.md](PUBLICAR_RAILWAY.md). Não divulgue o link até verificar a proteção por senha.

## Render Free (hospedagem para testes com poucos amigos)

- Use a opção **New > Blueprint** no painel Render, escolha este repositório e o arquivo `render.yaml`.
- O Blueprint seleciona `free` (0,1 vCPU / 512 MB de RAM) e solicita `APP_ACCESS_CODE` **no painel**, sem publicar senha no GitHub.
- O site será HTTPS num endereço `.onrender.com` e poderá ser instalado na tela inicial como PWA nos navegadores compatíveis. **Não funciona offline:** a conversão depende do servidor.
- A Render Free aceita pedidos de até 370 MB por arquivo, com 1 conversão simultânea, pausa individual de 60 segundos após processamento e retenção de 10 minutos. Não há limite fixo de duração; mas vídeos longos excederão facilmente o tamanho/recursos disponíveis.
- A Render suspende a instância após 15 minutos sem requisições; o próximo acesso pode esperar ~1 minuto. Arquivos temporários podem desaparecer ao suspender ou reiniciar.
- Se vídeos de boa resolução falharem, não aumente as cotas cegamente: monitore os logs. Limitações de plataforma, CPU, RAM, espaço e tráfego continuam existindo.
- Uso apenas de conteúdo próprio, público com permissão ou autorizado; não contorne paywalls, DRM ou sessões privadas.

Guia passo a passo em **PUBLICAR_RENDER.md**.

## VibeDrop 2.2 — runtime atualizado e controle de uso justo

- A tela de senha **continua ativa**. Não compartilhe o código em arquivos públicos.
- Não existe mais um limite **global** de 10 conversões por hora. Cada sessão tem um descanso de 60 segundos após o trabalho, sem contar pedidos por hora.
- Arquivos e estado de conversões são acessíveis apenas pela sessão que solicitou a mídia.
- A Render Free não garante que um vídeo de 370 MB caiba no armazenamento temporário: FFmpeg pode exigir múltiplos arquivos intermediários.
- O workspace Hobby da Render inclui 5 GB/mês de saída, compartilhados com outros serviços do workspace. O VibeDrop não mede o total mensal; consulte Billing e Metrics da Render.
- Os controles por sessão estão na memória e podem se perder com reinícios; a identificação de sessão pode ser reiniciada ao limpar cookies. Não são uma proteção suficiente para um site anônimo de grande escala.
