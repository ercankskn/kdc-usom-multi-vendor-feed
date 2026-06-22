#!/usr/bin/env bash
set -Eeuo pipefail

PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="mvfeed"
APP_GROUP="mvfeed"
APP_HOME="/opt/mvfeed"
PUBLIC_ROOT="/srv/mvfeed/public"
CONFIG_ROOT="/etc/mvfeed"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi

getent passwd "${APP_USER}" >/dev/null || \
  useradd --system --user-group --home-dir "${APP_HOME}" \
    --create-home --shell /usr/sbin/nologin "${APP_USER}"

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0750 \
  "${APP_HOME}/app" "${APP_HOME}/data" "${APP_HOME}/staging" \
  "${APP_HOME}/backups"
install -d -o root -g "${APP_GROUP}" -m 0750 "${CONFIG_ROOT}"
install -d -o "${APP_USER}" -g www-data -m 0755 "${PUBLIC_ROOT}"

install -o "${APP_USER}" -g "${APP_GROUP}" -m 0750 \
  "${PKG_DIR}/src/collector.py" "${APP_HOME}/app/collector.py"
install -o root -g root -m 0644 \
  "${PKG_DIR}/config/mvfeed.env.example" "${CONFIG_ROOT}/mvfeed.env.example"

if [[ ! -f "${CONFIG_ROOT}/mvfeed.env" ]]; then
  cp "${PKG_DIR}/config/mvfeed.env.example" "${CONFIG_ROOT}/mvfeed.env"
  chmod 0640 "${CONFIG_ROOT}/mvfeed.env"
fi

if [[ ! -f "${CONFIG_ROOT}/routes.json" ]]; then
  cp "${PKG_DIR}/config/routes.example.json" "${CONFIG_ROOT}/routes.json"
  chmod 0640 "${CONFIG_ROOT}/routes.json"
fi

for unit in mvfeed-full.service mvfeed-sync.service mvfeed-sync.timer; do
  install -o root -g root -m 0644 \
    "${PKG_DIR}/systemd/${unit}" "/etc/systemd/system/${unit}"
done

chown -R "${APP_USER}:${APP_GROUP}" "${APP_HOME}"
chown -R "${APP_USER}:www-data" "${PUBLIC_ROOT}"
python3 -m py_compile "${APP_HOME}/app/collector.py"
systemctl daemon-reload

echo
printf '%s\n' \
  "Installed successfully." \
  "1. Review ${CONFIG_ROOT}/routes.json and ${CONFIG_ROOT}/mvfeed.env" \
  "2. Start the initial sync: systemctl start mvfeed-full.service" \
  "3. Follow progress: journalctl -u mvfeed-full.service -f" \
  "4. Enable incremental sync after completion: systemctl enable --now mvfeed-sync.timer"
