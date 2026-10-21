# Preparação do lançamento — VibeDrop 2.0

O código do aplicativo deve ficar diretamente na raiz deste repositório, com `app.py`, `Dockerfile`, `requirements.txt`, `static/` e `templates/`. A implantação não está ativa até que todos os arquivos sejam publicados e a hospedagem configurada.

## Publicar a pasta do projeto pelo Fedora 44

Extraia a versão atualizada do ZIP **VibeDrop_2_0_Pronto_Railway_GitHub.zip** em `~/Downloads`. Depois:

```bash
sudo dnf install -y git rsync
cd ~/Downloads
git clone https://github.com/Jovem-henrique/VibeDrop-project.git
rsync -av --exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' --exclude='.env' \
  ~/Downloads/VibeDrop_2_0/ ~/Downloads/VibeDrop-project/
cd ~/Downloads/VibeDrop-project
git status
git add .
git commit -m "feat: VibeDrop 2.0 com audio e video multiplataforma"
git push origin main
```

Não comite `.env`, senhas, cookies, tokens ou arquivos de mídia.

## Hospedagem Railway

1. Em https://railway.com, crie um projeto com **Deploy from GitHub repo** e escolha este repositório.
2. O projeto usa Dockerfile e a configuração `railway.json`, com healthcheck `/health`.
3. Na aba **Variables**, defina `APP_ACCESS_CODE` (senha forte), `FLASK_SECRET_KEY` (chave aleatória), `PUBLIC_HTTPS=1`, `MIN_FREE_GB=2` e `MAX_FILE_MB=0`.
4. Gere a chave em sua máquina com `python3 -c 'import secrets; print(secrets.token_hex(32))'`. Não publique o valor.
5. Após build e deploy saudáveis, acesse **Settings > Networking > Generate Domain** e teste com senha antes de compartilhar.

**Atenção:** o plano gratuito pode não ter espaço suficiente para mídia. Planos pagos cobram recursos e tráfego; configure orçamento/alertas. O código evita limites arbitrários de duração/tamanho, mas a hospedagem tem recursos finitos. O download real pode ser restringido por YouTube, Instagram ou TikTok. Use somente conteúdos cujo download seja autorizado.

Guia detalhado está no arquivo `PUBLICAR_RAILWAY.md` incluído no ZIP.
