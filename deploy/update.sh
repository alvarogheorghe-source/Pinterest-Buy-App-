#!/usr/bin/env bash
# Neue Version vom GitHub holen und neu starten (als root):  bash /opt/malipin/deploy/update.sh
set -euo pipefail
DIR=/opt/malipin
sudo -u malipin git -C "$DIR" pull -q
sudo -u malipin "$DIR/.venv/bin/pip" install -q -r "$DIR/requirements-ai.txt"
cp "$DIR/deploy/"malipin*.service "$DIR/deploy/malipin-nightly.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl restart malipin
echo "Aktualisiert: $(sudo -u malipin git -C "$DIR" log --oneline -1)"
