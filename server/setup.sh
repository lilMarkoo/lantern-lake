#!/usr/bin/env bash
# Install (or update) the Lantern Lake relay on a Linux server, as a service that starts on boot.
# Run it from the folder holding relay.py and lantern-relay.service:   sudo bash setup.sh
# Works on Ubuntu and Oracle Linux, including Oracle Cloud's images (it opens the port in their firewall too).
set -euo pipefail
PORT="${PORT:-24690}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run it with sudo:  sudo bash setup.sh"; exit 1
fi
if ! command -v python3 >/dev/null; then
  if command -v apt-get >/dev/null; then apt-get update -q && apt-get install -y -q python3
  else dnf install -y python3; fi
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
  || { echo "Python 3.8 or newer is needed."; exit 1; }

install -d -m 755 /opt/lantern-relay
install -m 644 "$HERE/relay.py" /opt/lantern-relay/relay.py
sed "s/--port [0-9]*/--port $PORT/" "$HERE/lantern-relay.service" > /etc/systemd/system/lantern-relay.service
systemctl daemon-reload
systemctl enable lantern-relay >/dev/null 2>&1
systemctl restart lantern-relay

# open the port in the machine's own firewall (Oracle's images block everything but SSH by default)
if command -v firewall-cmd >/dev/null && systemctl is-active --quiet firewalld; then
  firewall-cmd --quiet --permanent --add-port="$PORT/tcp"
  firewall-cmd --quiet --reload
  echo "Opened TCP $PORT in firewalld."
elif command -v iptables >/dev/null; then
  if ! iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT -p tcp --dport "$PORT" -j ACCEPT
  fi
  if command -v netfilter-persistent >/dev/null; then
    netfilter-persistent save >/dev/null 2>&1 || true
  elif command -v apt-get >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q iptables-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true
  fi
  echo "Opened TCP $PORT in iptables (kept across reboots)."
fi

sleep 1
if systemctl is-active --quiet lantern-relay; then
  echo "The relay is running on port $PORT."
  echo "Check it from your PC:  python server/check.py <this server's public IP>"
else
  echo "The relay didn't start. See:  journalctl -u lantern-relay -n 50"; exit 1
fi
