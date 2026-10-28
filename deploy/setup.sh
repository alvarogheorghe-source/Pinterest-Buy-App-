#!/usr/bin/env bash
# Malipin auf einem frischen Ubuntu-24.04-Server einrichten (einmal als root ausführen).
#   bash setup.sh
# Danach: /opt/malipin/.env anlegen (siehe docs/SERVER.md) und  systemctl restart malipin
set -euo pipefail

REPO="https://github.com/alvarogheorghe-source/Pinterest-Buy-App-.git"
DIR=/opt/malipin

echo "== Pakete =="
apt-get update -q
apt-get install -y -q git python3-venv python3-pip debian-keyring debian-archive-keyring apt-transport-https curl ufw
# Caddy (Webserver mit automatischem HTTPS) aus der offiziellen Quelle
if ! command -v caddy >/dev/null; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q && apt-get install -y -q caddy
fi

echo "== Auslagerungsdatei (4 GB) =="
# Reserve, falls App und nächtliche Bilderkennung gleichzeitig viel Arbeitsspeicher brauchen
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "== Firewall: nur SSH und Web =="
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

echo "== Benutzer & Code =="
git config --global --add safe.directory "$DIR"   # Code gehört "malipin", root darf trotzdem pullen
id malipin >/dev/null 2>&1 || useradd --system --home "$DIR" --shell /usr/sbin/nologin malipin
if [ ! -d "$DIR/.git" ]; then git clone -q "$REPO" "$DIR"; else git -C "$DIR" pull -q; fi
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
# PyTorch ohne Grafikkarte (CPU) – viel kleiner als die Standard-Version
"$DIR/.venv/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cpu
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements-ai.txt"
mkdir -p "$DIR/data"
chown -R malipin:malipin "$DIR"
[ -f "$DIR/.env" ] && chmod 600 "$DIR/.env"

echo "== Dienste =="
cp "$DIR/deploy/malipin.service" "$DIR/deploy/malipin-nightly.service" "$DIR/deploy/malipin-nightly.timer" /etc/systemd/system/
cp "$DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now malipin malipin-nightly.timer
systemctl reload caddy || systemctl restart caddy

echo
echo "Fertig. Fehlt noch die .env? -> docs/SERVER.md, Schritt 4. Status:  systemctl status malipin"
