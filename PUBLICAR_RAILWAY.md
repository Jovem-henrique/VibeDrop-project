# Publicação do VibeDrop 2.0 na Railway

Este guia usa o repositório **Jovem-henrique/VibeDrop-project** e o Dockerfile incluído no projeto. A publicação **não foi realizada automaticamente**: exige conectar sua conta Railway, ativar plano/recursos e configurar segredos pessoais.

## 1. Publicar código no GitHub

A pasta raiz do repositório deve conter diretamente `app.py`, `Dockerfile`, `requirements.txt`, `railway.json`, `templates/` e `static/`; não crie a pasta `VibeDrop_2_0` dentro do repo.

No Fedora:

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

Se `git commit` pedir identidade, configure `git config --global user.name "SEU NOME"` e `git config --global user.email "EMAIL DO GITHUB"`. Se `git push` pedir autenticação, use o fluxo de login seguro do Git Credential Manager ou `gh auth login`, nunca coloque token no código nem no chat.

> Caso a pasta `~/Downloads/VibeDrop-project` já exista, pule `git clone` e execute `git -C ~/Downloads/VibeDrop-project pull --ff-only` antes da cópia, desde que não tenha alterações locais pendentes.

## 2. Criar serviço na Railway

1. Entre em https://railway.com/ e entre/crie a conta.
2. Em **New Project**, escolha **Deploy from GitHub repo** e selecione `Jovem-henrique/VibeDrop-project`.
3. Selecione um plano com recursos adequados (Hobby é a primeira opção para testes reais). Confirme preços e custos adicionais antes de contratar.
4. A Railway reconhecerá o **Dockerfile** na raiz. O `railway.json` configura health check em `/health`.
5. Na guia **Variables**, crie, sem compartilhar valores:

   | Variável | Valor |
   |---|---|
   | `APP_ACCESS_CODE` | Uma senha longa, criada por você |
   | `FLASK_SECRET_KEY` | Uma chave hex aleatória de 64 caracteres |
   | `PUBLIC_HTTPS` | `1` |
   | `MIN_FREE_GB` | `2` (reserva mínima; exige espaço livre superior a isso) |
   | `MAX_FILE_MB` | `0` (sem teto **arbitrário** por arquivo) |

   Gere a chave com: `python3 -c 'import secrets; print(secrets.token_hex(32))'`.

6. **Não configure** manualmente `PORT`, a Railway injeta essa variável; o Dockerfile já utiliza `${PORT}`.
7. Confirme o deploy e veja logs. Em **Settings > Networking > Public Networking**, use **Generate Domain** para criar a URL HTTPS.
8. Abra o domínio, confirme que solicita senha e teste links **autorizados** pequenos primeiro.
9. Configure alertas/limites de gastos e revise o uso de CPU, RAM, disco e tráfego.

## 3. Capacidades e limites reais

- O código não estabelece duração máxima nem tamanho máximo por padrão. **Isso não significa capacidade ilimitada da hospedagem.** A plataforma pode impor limites de memória, CPU, armazenamento, tráfego, custo e duração de requisições.
- Na Railway, projetos Free têm armazenamento efêmero restrito; com `MIN_FREE_GB=2`, não são adequados a conversões reais. O plano pago tem limites mais altos, mas os recursos usados podem gerar cobranças adicionais.
- Recomendo começar com uma instância, **uma réplica** e senha ativada. A fila é mantida em memória no único processo Gunicorn; múltiplas réplicas quebrariam o acompanhamento dos jobs sem uma fila externa.
- Arquivos convertidos permanecem temporariamente por aproximadamente 30 minutos após serem concluídos. Reinícios e novos deploys podem apagá-los mais cedo.
- O limite de até dois trabalhos simultâneos, a cota de 24 pedidos/hora e a reserva de disco permanecem para proteger o servidor.
- O uso de `yt-dlp` em servidores cloud pode sofrer restrições do YouTube/Instagram/TikTok, mesmo quando links funcionam no PC. Conteúdo privado/protegido não é suportado. Não há garantia de download de toda URL.
- Use apenas mídia própria ou cujo download e uso sejam autorizados. Respeite os termos das plataformas e direitos de terceiros.

## 4. Verificações antes de divulgar o endereço

- [ ] `/health` retorna `{"status":"ok"}`.
- [ ] A página principal redireciona para login sem senha válida.
- [ ] Página inicial, abas Áudio/Vídeo e miniaturas exibidas corretamente.
- [ ] MP3, M4A e MP4 com conteúdo autorizado testados em dispositivos diferentes.
- [ ] Três plataformas avaliadas conforme suas restrições.
- [ ] Cotas e histórico de custos observados e orçamento definido.
- [ ] Nenhumas credenciais, tokens ou arquivos baixados no GitHub.

Se precisar de mais armazenamento e custos mais previsíveis para mídia longa, considere no futuro um VPS com pelo menos dezenas de GB livres, contêiner isolado, HTTPS, monitoramento, firewall e política de cotas.
