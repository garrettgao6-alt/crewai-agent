#!/usr/bin/env bash
# Install isolated operational units; never restart application services.
set -euo pipefail
umask 077
[ "$(id -u)" -eq 0 ]
mkdir -p /etc/gaointelligence /var/lib/gaointelligence-ops
chmod 700 /etc/gaointelligence /var/lib/gaointelligence-ops
for unit in gao-monitor.service gao-monitor.timer gao-backup.service gao-backup.timer; do
    cp "/root/crewai-agent/deploy/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --now gao-monitor.timer
if [ -f /etc/gaointelligence/operations.env ] && grep -q '^RESTIC_REPOSITORY=' /etc/gaointelligence/operations.env; then
    systemctl enable --now gao-backup.timer
else
    echo BACKUP_TIMER_AWAITS_AUTHORIZED_DESTINATION
fi
# Immediate health check is performed separately so installation does not fail
# simply because an administrator has not configured remote storage yet.
echo OPERATIONS_TIMERS_INSTALLED
