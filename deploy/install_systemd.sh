#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo:"
  echo "  sudo bash deploy/install_systemd.sh"
  exit 1
fi

cd "$(dirname "$0")/.."

install -m 0644 deploy/garrett-api.service /etc/systemd/system/garrett-api.service
install -m 0644 deploy/garrett-streamlit.service /etc/systemd/system/garrett-streamlit.service

systemctl daemon-reload
systemctl enable garrett-api
systemctl enable garrett-streamlit
systemctl restart garrett-api
systemctl restart garrett-streamlit

echo
echo "Garrett Intelligence Hub systemd services installed."
echo
echo "Check status:"
echo "  systemctl status garrett-api"
echo "  systemctl status garrett-streamlit"
echo
echo "View logs:"
echo "  journalctl -u garrett-api -f"
echo "  journalctl -u garrett-streamlit -f"
echo
echo "Restart services:"
echo "  systemctl restart garrett-api"
echo "  systemctl restart garrett-streamlit"
