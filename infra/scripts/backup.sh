#!/usr/bin/env bash
# Backup diário: pg_dump comprimido (formato custom), retenção curta, checagem de espaço.
# Roda pelo timer systemd seismo-backup.timer. A cópia para fora é puxada do PC com pull-backup.ps1.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
DIR=${BACKUP_DIR:-/var/backups/seismo}
KEEP=${BACKUP_KEEP_DAYS:-7}
MIN_FREE_GB=${BACKUP_MIN_FREE_GB:-8}

FREE_GB=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
if [ "$FREE_GB" -lt "$MIN_FREE_GB" ]; then
  echo "ERRO: só ${FREE_GB} GB livres (mínimo ${MIN_FREE_GB}). Backup não feito." >&2
  exit 1
fi

STAMP=$(date -u +%Y%m%d-%H%M)
TMP="$DIR/.seismo-$STAMP.dump.partial"
OUT="$DIR/seismo-$STAMP.dump"
docker compose exec -T postgres pg_dump -U seismo -d seismo -Fc -Z 6 > "$TMP"
mv "$TMP" "$OUT"
echo "backup: $OUT ($(du -h "$OUT" | cut -f1))"

find "$DIR" -maxdepth 1 -name 'seismo-*.dump' -mtime +"$KEEP" -print -delete
find "$DIR" -maxdepth 1 -name '.seismo-*.partial' -mmin +120 -delete
