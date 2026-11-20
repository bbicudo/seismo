#!/usr/bin/env bash
# Atualiza o servidor a partir do GitHub: puxa o código, refaz as imagens que mudaram e sobe.
# .env, secrets/ e infra/caddy/auth.caddy ficam fora do git e não são tocados.
# Uso: infra/scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

before=$(git rev-parse HEAD)
git pull --ff-only
after=$(git rev-parse HEAD)
if [ "$before" = "$after" ]; then
  echo "Nada novo no GitHub ($after)."
  exit 0
fi
echo "Atualizando $before -> $after"
git --no-pager log --oneline "$before..$after"

# cria arquivos novos que o compose monta (sem eles, o Docker criaria pastas no lugar)
infra/scripts/init-env.sh >/dev/null
for f in infra/caddy/auth.caddy infra/caddy/admin.caddy; do
  [ -f "$f" ] || { echo "ERRO: $f não existe (ou virou pasta). Corrija antes de subir."; exit 1; }
done

docker compose build
docker compose up -d
docker compose ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
