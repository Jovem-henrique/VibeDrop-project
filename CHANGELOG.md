# VibeDrop 2.1 — Render Free (21/10/2026)

- Correção operacional: a imagem Docker instala a versão nightly do yt-dlp, recomendada pelo projeto quando mudanças nas plataformas quebram o extrator estável.
- Os logs de inicialização registram a versão do yt-dlp usada pelo serviço.
- Mensagens específicas para limite de acesso anônimo do Instagram e falha de extração do player do YouTube.
- Testes offline para as mensagens de erro das duas plataformas.

- Teto de 370 MB por arquivo, sem limite fixo de duração.
- Removida a cota compartilhada de 10 conversões/hora.
- Uma conversão ativa por vez e pausa individual de 60 segundos após conclusão.
- Os resultados ficam vinculados à sessão original.
- Mantidas senha, limites de prévia, proteção de espaço e URL.

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
