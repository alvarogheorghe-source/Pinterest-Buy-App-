#!/bin/bash
# Malipin – Sicherheits-Check für den Server. NUR LESEN: ändert nichts, zeigt keine Geheimnisse.
# Aufruf auf dem Server (als root):  bash /opt/malipin/scripts/server_check.sh
# Ausgabe: OK / WARNUNG / INFO je Punkt, am Ende eine Zusammenfassung.

APP=/opt/malipin
WARN=0
ok()   { echo "  OK       $*"; }
warn() { echo "  WARNUNG  $*"; WARN=$((WARN+1)); }
info() { echo "  INFO     $*"; }
head_() { echo; echo "== $*"; }

# Gibt den Wert einer Einstellung aus .env zurück, nur um zu prüfen, OB sie gesetzt ist (wird nie angezeigt).
env_value() { [ -r "$APP/.env" ] && grep -E "^$1=" "$APP/.env" | tail -1 | cut -d= -f2- | tr -d '"'"'"' '; }

head_ "System"
info "$(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME"), Kernel $(uname -r)"
if command -v apt-get >/dev/null; then
  n=$(apt-get -s -o Debug::NoLocking=1 upgrade 2>/dev/null | grep -c '^Inst ')
  [ "$n" -eq 0 ] && ok "keine ausstehenden Updates" || warn "$n Pakete können aktualisiert werden (apt update && apt upgrade)"
  s=$(apt-get -s -o Debug::NoLocking=1 upgrade 2>/dev/null | grep '^Inst ' | grep -ci security)
  [ "$s" -gt 0 ] && warn "davon $s Sicherheits-Updates"
fi
dpkg -s unattended-upgrades >/dev/null 2>&1 && ok "automatische Sicherheits-Updates installiert" \
  || warn "unattended-upgrades fehlt (apt install unattended-upgrades)"
[ -f /var/run/reboot-required ] && warn "Neustart nötig (reboot)"

head_ "Firewall und offene Ports"
if command -v ufw >/dev/null; then
  ufw status 2>/dev/null | grep -q "Status: active" && ok "ufw aktiv" || warn "ufw ist nicht aktiv"
  ufw status 2>/dev/null | grep -E "ALLOW" | sed 's/^/           /'
else
  warn "ufw nicht installiert"
fi
echo "  Ports, die von außen erreichbar sein könnten:"
ss -tulnH 2>/dev/null | awk '{print $1, $5}' | grep -vE ' (127\.|\[::1\]|::1)' | sort -u | sed 's/^/           /'
ss -tlnH 2>/dev/null | awk '{print $4}' | grep -qE '^(0\.0\.0\.0|\*|\[::\]):8000$' \
  && warn "App-Port 8000 lauscht auf allen Adressen – sollte nur 127.0.0.1 sein" \
  || ok "App-Port 8000 nur lokal"

head_ "SSH"
cfg=$(sshd -T 2>/dev/null)
if [ -n "$cfg" ]; then
  pa=$(echo "$cfg" | awk '/^passwordauthentication /{print $2}')
  prl=$(echo "$cfg" | awk '/^permitrootlogin /{print $2}')
  [ "$pa" = "no" ] && ok "Passwort-Login aus" || warn "Passwort-Login an (erst SSH-Schlüssel einrichten, dann ausschalten)"
  case "$prl" in
    no|prohibit-password|without-password) ok "root-Login nur mit Schlüssel ($prl)";;
    *) warn "root darf sich mit Passwort anmelden (PermitRootLogin $prl)";;
  esac
else
  info "sshd -T nicht lesbar (als root ausführen)"
fi
keys=$(grep -cE '^(ssh-|ecdsa-|sk-)' /root/.ssh/authorized_keys 2>/dev/null || echo 0)
info "$keys SSH-Schlüssel für root hinterlegt – unbekannte Schlüssel sofort entfernen"
if systemctl is-active --quiet fail2ban 2>/dev/null; then ok "fail2ban läuft"
else warn "fail2ban läuft nicht (apt install fail2ban)"; fi
fails=$(journalctl -u ssh -u sshd --since "24 hours ago" 2>/dev/null | grep -ci "failed password")
info "fehlgeschlagene SSH-Passwort-Versuche in 24 h: $fails"

head_ "Dienste"
for s in malipin caddy; do
  systemctl is-active --quiet $s && ok "$s läuft" || warn "$s läuft nicht"
done
systemctl is-active --quiet malipin-nightly.timer && ok "nächtlicher Job geplant" || warn "malipin-nightly.timer nicht aktiv"
u=$(systemctl show -p User --value malipin 2>/dev/null)
[ "$u" = "malipin" ] && ok "App läuft als Benutzer malipin (nicht root)" || warn "App-Benutzer ist '${u:-root}'"
for opt in NoNewPrivileges ProtectSystem ProtectHome PrivateTmp UMask; do
  info "$opt=$(systemctl show -p $opt --value malipin 2>/dev/null)"
done
[ "$(systemctl show -p NoNewPrivileges --value malipin 2>/dev/null)" = "yes" ] \
  || warn "Härtung nicht aktiv – deploy/malipin.service neu kopieren + systemctl daemon-reload"

head_ "Dateirechte"
check_mode() { # Pfad, erlaubter Höchstwert als Text, Prüf-Regex für Modus
  [ -e "$1" ] || { info "$1 fehlt"; return; }
  m=$(stat -c '%a %U' "$1")
  echo "$m" | grep -qE "$2" && ok "$1 ($m)" || warn "$1 ist $m – erwartet: $3"
}
check_mode "$APP/.env" '^(600|400) (malipin|root)$' "600, Besitzer malipin (chmod 600 .env)"
check_mode "$APP/data" '^700 malipin$' "700 malipin (chmod 700 data)"
check_mode "$APP/backups" '^700 malipin$' "700 malipin (chmod 700 backups)"
loose=$(find "$APP/data" "$APP/backups" -perm /o+r 2>/dev/null | wc -l)
[ "$loose" -eq 0 ] && ok "keine Daten-Dateien für andere lesbar" || warn "$loose Dateien in data/backups für alle lesbar (chmod -R go-rwx data backups)"
(cd "$APP" 2>/dev/null && git check-ignore -q .env 2>/dev/null) && ok ".env ist von git ignoriert" || warn ".env NICHT in .gitignore"
(cd "$APP" 2>/dev/null && git ls-files --error-unmatch .env >/dev/null 2>&1) && warn ".env ist im git-Repo eingecheckt!"

head_ "Einstellungen in .env (nur ob gesetzt, Werte werden nicht gezeigt)"
for k in SESSION_SECRET ADMIN_PASSWORD PUBLIC_URL MULTI_USER PINTEREST_CLIENT_ID PINTEREST_CLIENT_SECRET PINTEREST_REDIRECT_URI; do
  v=$(env_value $k)
  [ -n "$v" ] && ok "$k gesetzt" || warn "$k fehlt"
done
v=$(env_value SESSION_SECRET); [ -n "$v" ] && [ ${#v} -lt 32 ] && warn "SESSION_SECRET ist kürzer als 32 Zeichen"
v=$(env_value ADMIN_PASSWORD); [ -n "$v" ] && [ ${#v} -lt 14 ] && warn "ADMIN_PASSWORD ist kürzer als 14 Zeichen"
[ "$(env_value MULTI_USER)" = "1" ] && ok "MULTI_USER=1 (jede:r Besucher:in hat eigene Daten)" \
  || warn "MULTI_USER ist nicht 1 – alle Besucher:innen teilen sich ein Konto!"
case "$(env_value PUBLIC_URL)" in https://*) ok "PUBLIC_URL ist https";; *) warn "PUBLIC_URL ist nicht https://…";; esac
unset v

head_ "Website (lokal geprüft)"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/health)
[ "$code" = "200" ] && ok "App antwortet lokal" || warn "App antwortet lokal nicht (HTTP $code)"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/docs)
case "$code" in 404) ok "/docs ist aus";; 000) info "/docs nicht prüfbar (App aus)";; *) warn "/docs ist erreichbar (HTTP $code) – PUBLIC_URL prüfen";; esac
days=$(echo | timeout 5 openssl s_client -connect malipin.com:443 -servername malipin.com 2>/dev/null \
  | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
[ -n "$days" ] && info "HTTPS-Zertifikat gültig bis: $days" || warn "HTTPS-Zertifikat nicht lesbar"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://malipin.com/)
case "$code" in 301|308) ok "http leitet auf https um";; *) info "http → HTTP $code";; esac

head_ "Backups und Speicher"
last=$(ls -t "$APP"/backups 2>/dev/null | head -1)
[ -n "$last" ] && info "letztes Backup: $last" || warn "keine Backups gefunden"
df -h / | awk 'NR==2{print "  INFO     Platte: "$3" belegt, "$4" frei ("$5")"}'
use=$(df / | awk 'NR==2{gsub("%","",$5); print $5}'); [ "$use" -gt 85 ] && warn "Platte über 85 % voll"

echo
if [ "$WARN" -eq 0 ]; then echo "Ergebnis: alles in Ordnung."
else echo "Ergebnis: $WARN Warnung(en) – Liste oben. Ausgabe gern an Claude schicken (sie enthält keine Geheimnisse)."; fi
