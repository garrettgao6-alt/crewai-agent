#!/usr/bin/env bash
set -euo pipefail
umask 077
app=/root/crewai-agent
sha=$(cat "$app/.release_sha")
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 1
runtime="/root/gao-releases/$sha/venv/bin/python"
cd "$app"
exec "$runtime" "$app/deploy/operations.py" "${1:?operation required}"
