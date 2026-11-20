#!/usr/bin/env bash
# Operação do dia a dia. Rode na pasta do projeto no servidor.
#   seismo.sh pause | resume        pausa ou libera o coletor sem derrubar nada
#   seismo.sh status                containers, coletor, requisições, disco, memória, limite de saída
#   seismo.sh logs [serviço]        últimos logs
#   seismo.sh lab-user <nome>       cria/troca o usuário do basic auth (pede a senha sem mostrar)
#   seismo.sh admin-user <nome>     cria/troca o login da área /admin (pede a senha sem mostrar)
#   seismo.sh prune                 limpa imagens e cache de build com mais de 7 dias
set -euo pipefail
cd "$(dirname "$0")/../.."
DC="docker compose"
redis() { $DC exec -T redis redis-cli "$@"; }

case "${1:-status}" in
  pause)
    redis SET seismo:paused 1 >/dev/null && echo "coletor PAUSADO (termina a rodada atual e para)";;
  resume)
    redis SET seismo:paused 0 >/dev/null && echo "coletor LIBERADO";;
  status)
    $DC ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
    echo; echo "== coletor"
    echo "pausado:        $(redis GET seismo:paused)"
    echo "última rodada:  $(redis GET seismo:last_cycle_at)  ($(redis GET seismo:last_cycle_seconds) s, $(redis GET seismo:last_cycle_worlds) mundos)"
    echo "requisições hoje: $(redis GET "seismo:requests:$(date -u +%F)")   erros hoje: $(redis GET "seismo:errors:$(date -u +%F)")"
    echo; echo "== disco"; df -h / | tail -1; docker system df
    echo; echo "== memória"; free -h | head -2
    docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
    if [ -n "${IFACE:-}" ]; then echo; echo "== fila de saída ($IFACE)"; tc qdisc show dev "$IFACE"; fi;;
  logs)
    $DC logs --tail 100 "${2:-collector}";;
  lab-user|admin-user)
    FILE=infra/caddy/$([ "$1" = admin-user ] && echo admin || echo auth).caddy
    # nomes de área diferentes: o navegador guarda uma senha para cada área e não mistura as duas
    REALM=$([ "$1" = admin-user ] && echo "Seismo admin" || echo "Seismo lab")
    NAME=${2:?informe o nome do usuário}
    read -r -s -p "Senha para $NAME: " PW; echo
    read -r -s -p "Repita a senha: " PW2; echo
    [ "$PW" = "$PW2" ] || { echo "As senhas não conferem."; exit 1; }
    # o caddy lê a senha do stdin até a quebra de linha (sem ela, dá "Error: EOF")
    HASH=$(printf '%s\n' "$PW" | docker run --rm -i caddy:2.10.0-alpine caddy hash-password)
    unset PW PW2
    case "$HASH" in \$2*) ;; *) echo "Falha ao gerar o hash. Nada foi gravado."; exit 1;; esac
    printf 'basic_auth bcrypt "%s" {\n\t%s %s\n}\n' "$REALM" "$NAME" "$HASH" > "$FILE"
    chmod 0644 "$FILE"
    echo "$FILE gravado (só o hash)."
    if $DC ps --status running caddy | grep -q caddy; then $DC exec -T caddy caddy reload --config /etc/caddy/Caddyfile && echo "Caddy recarregado."; fi;;
  prune)
    docker image prune -af --filter "until=168h"
    docker builder prune -af --filter "until=168h";;
  *)
    sed -n '2,8p' "$0"; exit 1;;
esac
