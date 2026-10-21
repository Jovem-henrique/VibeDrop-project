# VibeDrop 2.2 — atualização completa do runtime (21/10/2026)

- Python atualizado para 3.14.8 (imagem oficial `python:3.14.8-slim`).
- Flask fixado em 3.1.3 e Gunicorn em 26.2.2.
- yt-dlp fixado ao commit upstream `f59cd0ba0a3c666fa5d8793b073fa9f03cfecc22`, que inclui a correção de extração inicial do YouTube publicada em 21/10/2026.
- FFmpeg atualizado para a linha 9.0.2; build Linux x86_64 fixado e verificado por SHA-256.
- Deno atualizado para 2.9.8; binário oficial fixado e verificado por SHA-256.
- A construção da imagem imprime as versões dos runtimes e das bibliotecas principais para facilitar diagnósticos.
- CI atualizado para testar em Python 3.14.
- Logs verbosos do yt-dlp permanecem ativados temporariamente para diagnosticar extração; desativar `YTDLP_VERBOSE` após confirmar o funcionamento.
- Mantidas a senha, a validação de URLs, o teto de 370 MB por arquivo, uma conversão simultânea, pausa de 60 segundos por sessão e a hospedagem Render Free.
- Os testes automatizados são offline; a confirmação de downloads reais depende de um teste do serviço publicado.

## VibeDrop 2.1 — Render Free (21/10/2026)

- Teto de 370 MB por arquivo, sem limite fixo de duração.
- Removida a cota compartilhada de 10 conversões/hora.
- Uma conversão ativa por vez e pausa individual de 60 segundos após conclusão.
- Os resultados ficam vinculados à sessão original.
- Mantidas senha, limites de prévia, proteção de espaço e URL.
- Diagnóstico temporário de falhas do yt-dlp; testes com a versão estável e nightly mostraram que a falha do YouTube exigia investigar mudanças mais recentes do extrator.

# Histórico de versões

## VibeDrop 2.0 — protótipo local

- Interface original preservada com opção de **Áudio / Vídeo**.
- Suporte a MP3, M4A e MP4, com seleções de resolução do vídeo.
- Links individuais públicos do YouTube, Instagram e TikTok (conforme disponibilidade).
- Prévia opcional de metadados.
- Remove limite de duração e o teto padrão de 500 MB.
- Adiciona proteção por espaço livre no disco.
- Remove expiração arbitrária da espera em navegador para vídeos longos.
- Acrescenta testes e documentação de portfólio.

## VibeDrop 1.x — versão inicial

- Conversor web de vídeos individuais do YouTube em MP3/M4A.
- Interface com tema escuro, progresso e download temporário.
- Proteção por senha opcional, controles de uso e Cloudflare Tunnel para testes.

### Preparação para publicação — 2026-10-21
- Configuração `railway.json` com Docker e healthcheck; guia de publicação e segurança em `PUBLICAR_RAILWAY.md`.

## Render Free + PWA (2026-10-21)
- Blueprint gratuito com limite conservador de recursos, senha obrigatória, healthcheck.
- Identidade visual original preservada. Manifest e ícones PWA adicionados para tela inicial.
- Quantidade de tarefas e expiração configuráveis via variáveis de ambiente.

