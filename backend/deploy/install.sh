#!/bin/sh
# Run from the repository root on the droplet after inspecting the deploy files.
# This installs only the store service. It preserves existing Caddy sites.
set -eu
test "$(id -u)" = 0 || { echo 'Run as root.' >&2; exit 1; }
test -f backend/app.py
id roddystore >/dev/null 2>&1 || useradd --system --home /var/lib/roddy-store --shell /usr/sbin/nologin roddystore
install -d -m 755 /opt/roddy-store /opt/roddy-store/backend
cp -R backend/. /opt/roddy-store/backend/
chown -R root:root /opt/roddy-store/backend
chmod -R go-w /opt/roddy-store/backend
python3 -m venv /opt/roddy-store/venv
/opt/roddy-store/venv/bin/pip install -r /opt/roddy-store/backend/requirements.txt
install -d -o roddystore -g roddystore -m 700 /var/lib/roddy-store
install -d -o root -g roddystore -m 750 /var/lib/roddy-store/files /etc/roddy-store
if [ ! -f /etc/roddy-store/store.env ]; then
    install -o root -g roddystore -m 640 backend/deploy/store.env.example /etc/roddy-store/store.env
fi
if [ ! -f /etc/roddy-store/digital-products.json ]; then
    install -o root -g roddystore -m 640 backend/deploy/digital-products.json.example /etc/roddy-store/digital-products.json
fi
install -m 644 backend/deploy/roddy-store.service /etc/systemd/system/roddy-store.service
systemctl daemon-reload
systemctl enable --now roddy-store
echo 'Store service installed. Configure private files and Square before enabling checkout.'
