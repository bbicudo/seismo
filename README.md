# Seismo

*Sinta o tremor de cada mundo · Feel every world shake*

Fansite de Tibia que se atualiza sozinho e cobre todos os mundos: quem está online, quando cada mundo
joga (mapa de calor anônimo), saúde dos mundos, guilds, casas e leilões, e o histórico de kill
statistics que vai virar a detecção de raids. Site em português e inglês.

> Em laboratório. Os dados vêm da [TibiaData](https://tibiadata.com/). Tibia é marca registrada da CipSoft GmbH.

## Como funciona

```
TibiaData ──► coletor (Python) ──► Redis (quem está online agora)
                     │
                     └──────────► PostgreSQL (histórico e agregados) ──► API (FastAPI) ──► site (Next.js, pt/en)
                                                                                              │
                                                                               Caddy (HTTPS) ◄┘
```

- **A cada 5 minutos:** a lista de mundos e a foto de online de cada mundo. O diff entre fotos gera
  minutos por dia de jogo, level do mês, transfers e contadores anônimos por vocação × faixa × hora.
- **Uma vez por dia** (depois do server save): kill statistics, lista de guilds, casas e leilões.
- **Ao longo do dia:** detalhes de guild (a cada 3 dias por guild) e de casa (dono), aos poucos.
- No máximo 2 pedidos simultâneos e 2 por segundo, com backoff exponencial e `Retry-After`.

## Privacidade

- Nenhum horário de presença por personagem é guardado: só o total de minutos por dia e o último dia visto.
- Mapas de calor só agregados. Com filtro, células com menos de 5 jogadores não aparecem.
- Status online/offline de membros de guild não é guardado.
- Opt-out previsto para a versão pública.

## Estrutura

| Pasta | O quê |
|---|---|
| `collector/` | Coletor Python (httpx, Redis, psycopg) |
| `api/` | API FastAPI e migrações Alembic |
| `web/` | Site Next.js (output standalone), pt e en |
| `infra/` | Caddy, daemon.json do Docker, scripts de operação, backup e timers systemd |

## Rodar

Tudo roda com Docker Compose. As imagens são multi-arch (`linux/arm64` e `linux/amd64`).

```bash
sudo infra/scripts/bootstrap-docker.sh   # instala o Docker (Ubuntu 24.04)
infra/scripts/init-env.sh                # cria .env e a senha interna do Postgres
infra/scripts/seismo.sh lab-user <nome>  # usuário do basic auth do lab
docker compose up -d --build
infra/scripts/seismo.sh resume           # o coletor começa pausado
infra/scripts/seismo.sh status
```

## Imagens

O GitHub Actions ([`images.yml`](.github/workflows/images.yml)) roda os testes e publica as imagens
multi-arch (`linux/amd64` + `linux/arm64`, cada uma buildada num runner nativo) no GitHub Container Registry
a cada push no `main` e em tags `v*`:

- `ghcr.io/bbicudo/seismo-collector`, `ghcr.io/bbicudo/seismo-api`, `ghcr.io/bbicudo/seismo-web`
- tags: `main`, `sha-<commit>` e, em releases, `<versão>`

Para usar as imagens prontas em vez de buildar: no `.env`, `REGISTRY=ghcr.io/bbicudo` e `SEISMO_TAG=main`
(ou uma versão), depois `docker compose pull && docker compose up -d`.

Build multi-arch local, sem o Actions: `REGISTRY=ghcr.io/<usuario> TAG=<versão> docker buildx bake --push`.
