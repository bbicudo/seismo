#!/usr/bin/env bash
# Prepara .env, a senha interna do Postgres e a pasta de backup. Idempotente: não sobrescreve o que já existe.
# A senha é gerada aqui no servidor e nunca é mostrada na tela.
# Uso: infra/scripts/init-env.sh   (na pasta do projeto)
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env ] || { cp .env.example .env; echo ".env criado a partir do .env.example"; }

install -d -m 0700 secrets
if [ ! -s secrets/postgres_password ]; then
  umask 022
  openssl rand -base64 36 | tr -d '\n/+=' | head -c 40 > secrets/postgres_password
  chmod 0644 secrets/postgres_password   # legível pelos containers; a pasta secrets/ é 0700 no host
  echo "senha do Postgres gerada em secrets/postgres_password"
fi

[ -f infra/caddy/auth.caddy ] || echo "AVISO: falta infra/caddy/auth.caddy. Crie com: infra/scripts/seismo.sh lab-user <nome>"

BACKUP_DIR=$(grep -E '^BACKUP_DIR=' .env | cut -d= -f2 | cut -d' ' -f1)
sudo install -d -m 0750 -o "$(id -u)" -g "$(id -g)" "${BACKUP_DIR:-/var/backups/seismo}"
echo "pasta de backup: ${BACKUP_DIR:-/var/backups/seismo}"
