# Publicar VibeDrop na Render — plano gratuito

## 1. Enviar o código ao GitHub

1. No computador Fedora, extraia este ZIP e abra um terminal **dentro da pasta `VibeDrop_2_0`**.
2. Clone o repositório que você já criou: `git clone https://github.com/Jovem-henrique/VibeDrop-project.git` (de preferência fora da pasta do ZIP).
3. Copie todos os arquivos do projeto para a raiz do clone, incluindo `app.py`, `static/`, `templates/`, `tests/`, `Dockerfile` e `render.yaml`. Nunca copie `.venv`, `.env`, pastas `__pycache__` ou senhas.
4. No repositório local: `git add . && git commit -m "feat: VibeDrop 2.0 Render Free e PWA" && git push origin main`.

## 2. Criar o serviço gratuito

1. Acesse https://dashboard.render.com/. Crie uma conta gratuita ou entre na existente.
2. Clique em **New > Blueprint** e conecte o GitHub, autorizando acesso a `Jovem-henrique/VibeDrop-project`.
3. Selecione o repositório; a Render deve detectar `render.yaml`. Revise: `type: web`, `runtime: docker`, `plan: free`. Não aceite mudança involuntária para plano pago.
4. Informe **APP_ACCESS_CODE** quando o painel solicitar. Use uma senha forte, diferente da senha do GitHub. O `FLASK_SECRET_KEY` será gerado automaticamente.
5. Clique em **Apply** para construir e publicar. O primeiro build pode levar alguns minutos (Python, yt-dlp, FFmpeg, Deno).
6. Teste a URL `https://...onrender.com/health` e depois a página de login. Faça conversão de mídia curta **com autorização de download**.

## 3. Uso pelo celular como aplicativo

No Chrome Android, abra a URL HTTPS do VibeDrop, abra o menu e toque em **Instalar app** (ou **Adicionar à tela inicial**, dependendo do navegador). O PWA exige conexão à internet.

## Limites e transparência

- Configuração 2.1: até 370 MB por arquivo, uma conversão por vez, sem cota global de 10 solicitações/hora; pausa individual de 60 segundos depois de cada trabalho. Essas restrições são de recursos, e não um limite arbitrário na duração.
- Instâncias grátis podem hibernar, reiniciar e apagar arquivos locais temporários; links para arquivos só funcionam enquanto a instância e a tarefa existirem.
- CPU 0,1 e 512 MB RAM podem ser insuficientes para conversões de vídeo mais longas. A Render limita tráfego e horas grátis. Não é serviço de hospedagem garantidamente 24x7.
- Alguns provedores restringem a extração em IPs de datacenter; nem todo vídeo autorizado estará disponível.
- O código é público, mas a senha fica apenas nas variáveis de ambiente da Render.
- Não use o Flask embutido para produção; o Dockerfile já usa Gunicorn.
- Se falhar o build, vá em **Events / Logs** no painel Render e verifique qual etapa caiu.
- Custos: a opção `plan: free` não tem mensalidade, mas confira periodicamente os limites e faturamento no seu painel Render.
