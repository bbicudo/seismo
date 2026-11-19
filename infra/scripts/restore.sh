#!/usr/bin/env bash
# Restaura um dump no banco do Seismo. APAGA o banco atual.
# Uso: CONFIRM=sim infra/scripts/restore.sh /caminho/seismo-AAAAMMDD-HHMM.dump
set -euo pipefail
cd "$(dirname "$0")/../.."
FILE=${1:?informe o arquivo .dump}
[ -f "$FILE" ] || { echo "Arquivo não encontrado: $FILE"; exit 1; }
[ "${CONFIRM:-}" = "sim" ] || { echo "Isto apaga o banco atual. Rode de novo com CONFIRM=sim."; exit 1; }

docker compose stop collector api web
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U seismo -d postgres >/dev/null 2>&1; do sleep 2; done
docker compose exec -T postgres psql -U seismo -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS seismo WITH (FORCE);" -c "CREATE DATABASE seismo OWNER seismo;"
docker compose exec -T postgres pg_restore -U seismo -d seismo --no-owner --exit-on-error < "$FILE"
docker compose up -d
echo "Restauração concluída a partir de $FILE"
