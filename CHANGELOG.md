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
