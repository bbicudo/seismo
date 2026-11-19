#!/usr/bin/env bash
# Instala o Docker Engine pelo repositório oficial (Ubuntu) e aplica o daemon.json.
# Não grava regras de firewall. Opcional: CHECK_QDISC="<texto>" e IFACE=<interface> fazem o script
# abortar se a fila de saída da interface não contiver esse texto, e conferir de novo no fim.
# Uso: sudo infra/scripts/bootstrap-docker.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Rode com sudo."; exit 1; }
REPO_DIR=$(cd "$(dirname "$0")/../.." && pwd)
IFACE=${IFACE:-}
CHECK_QDISC=${CHECK_QDISC:-}
RULES=/etc/iptables/rules.v4

check_qdisc() {
  [ -n "$IFACE" ] && [ -n "$CHECK_QDISC" ] || return 0
  tc qdisc show dev "$IFACE" | grep -q "$CHECK_QDISC"
}

if ! check_qdisc; then echo "ERRO: fila de saída de $IFACE sem '$CHECK_QDISC'. Abortando."; exit 1; fi
RULES_SHA_BEFORE=$([ -f "$RULES" ] && sha256sum "$RULES" | cut -d' ' -f1 || echo none)

echo "== repositório oficial do Docker"
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update

echo "== daemon.json (rotação de logs) antes do primeiro start"
install -d -m 0755 /etc/docker
install -m 0644 "$REPO_DIR/infra/docker/daemon.json" /etc/docker/daemon.json

echo "== instalando Docker Engine, buildx e compose"
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "${SUDO_USER:-ubuntu}"
systemctl enable --now docker
systemctl restart docker

echo "== validações"
docker version --format 'Docker {{.Server.Version}} ({{.Server.Arch}})'
docker compose version
docker buildx version
OUT=$(docker run --rm alpine:3.22.1 sh -c 'wget -qO- https://api.tibiadata.com/v4/worlds | head -c 120' || true)
if [ -n "$OUT" ]; then echo "container acessa a internet: OK"; else echo "ATENÇÃO: container sem acesso à internet (ver chain FORWARD)"; fi
if check_qdisc; then echo "fila de saída: OK"; else echo "ATENÇÃO: fila de saída mudou!"; fi
RULES_SHA_AFTER=$([ -f "$RULES" ] && sha256sum "$RULES" | cut -d' ' -f1 || echo none)
[ "$RULES_SHA_BEFORE" = "$RULES_SHA_AFTER" ] && echo "regras de firewall salvas intactas: OK" || echo "ATENÇÃO: $RULES mudou"
echo "Pronto. Saia e entre de novo no SSH para o grupo docker valer."
