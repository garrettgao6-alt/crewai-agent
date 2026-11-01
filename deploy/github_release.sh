#!/usr/bin/env bash
# Authentication must succeed before any production mutation.
set -euo pipefail
umask 077
mode=${1:-verify}
target=${2:?Exact release SHA required}
case "$mode" in verify|backup|deploy) ;; *) echo 'Invalid release operation' >&2; exit 2;; esac
[[ "$target" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid release SHA' >&2; exit 2; }
host=209.38.93.248
trusted_host_digest=81647e644f59cd3f4485129bc7695536eb0bd5e6bd4ce55b492c0df163f83d22
repo=$(cd "$(dirname "$0")/.." && pwd)
keydir=$(mktemp -d)
trap 'rm -rf "$keydir"' EXIT
if [ -z "${SERVER_KEY:-}" ]; then
    echo '::error title=Missing SSH credential::SERVER_SSH_KEY is empty. No server changes were made.'
    exit 1
fi
printf '%s\n' "$SERVER_KEY" | tr -d '\r' > "$keydir/identity"
unset SERVER_KEY
chmod 600 "$keydir/identity"
if ! ssh-keygen -y -P '' -f "$keydir/identity" > "$keydir/identity.pub" 2>/dev/null; then
    echo '::error title=Invalid SSH credential::SERVER_SSH_KEY must be a complete, unencrypted OpenSSH private key. Its contents were not printed.'
    exit 1
fi
fingerprint=$(ssh-keygen -lf "$keydir/identity.pub")
echo "Deployment identity: $fingerprint"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
        printf '### Production deployment identity\n\n%s\n\nPublic key (not a secret):\n\n```text\n' "$fingerprint"
        cat "$keydir/identity.pub"
        printf '```\n\nOperation: `%s`; commit: `%s`.\n' "$mode" "$target"
    } >> "$GITHUB_STEP_SUMMARY"
fi
if ! ssh-keyscan -T 15 -t ed25519 "$host" > "$keydir/known_hosts" 2>/dev/null; then
    echo '::error title=Server unreachable::Could not retrieve the server host key. Check the server address, SSH port and firewall. No server changes were made.'
    exit 1
fi
python3 - "$keydir/known_hosts" "$trusted_host_digest" "$host" <<'PY'
import base64, hashlib, hmac, pathlib, sys
lines=pathlib.Path(sys.argv[1]).read_text().splitlines()
if len(lines)!=1:
    raise SystemExit('Expected exactly one SSH host key; no connection attempted.')
host,kind,key=lines[0].split()
digest=hashlib.sha256(base64.b64decode(key,validate=True)).hexdigest()
if host!=sys.argv[3] or kind!='ssh-ed25519' or not hmac.compare_digest(digest,sys.argv[2]):
    raise SystemExit('SSH host identity differs from the identity verified through the server console. No connection attempted.')
print('SSH host identity verified')
PY
ssh_options=(-i "$keydir/identity" -o IdentitiesOnly=yes -o IdentityAgent=none
    -o BatchMode=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no
    -o KbdInteractiveAuthentication=no -o ConnectTimeout=15 -o ConnectionAttempts=1
    -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$keydir/known_hosts"
    -o ServerAliveInterval=15 -o ServerAliveCountMax=3)
if ! ssh "${ssh_options[@]}" "root@$host" 'test "$(id -u)" -eq 0 && test -d /root/crewai-agent && command -v python3 >/dev/null && echo SSH_AUTHENTICATION_VERIFIED'; then
    echo '::error title=SSH authentication failed::The validated deployment key was rejected by the current server. Compare the public-key fingerprint in the job summary with the server authorized_keys. No application or data changes were made.'
    exit 1
fi
if [ "$mode" = verify ]; then
    ssh "${ssh_options[@]}" "root@$host" 'systemctl is-active crewai garrett-api && curl --fail --silent http://127.0.0.1:8501/_stcore/health && curl --fail --silent http://127.0.0.1:8000/health && cat /root/crewai-agent/.release_sha'
else
    # An old run must never replace a newer main release.
    latest=$(git ls-remote https://github.com/garrettgao6-alt/crewai-agent.git refs/heads/main | cut -f1)
    if [ "$latest" != "$target" ]; then
        echo "Superseded commit $target; current main is $latest. No production changes made."
        if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then echo 'Superseded commit: production operation skipped.' >> "$GITHUB_STEP_SUMMARY"; fi
        exit 0
    fi
    remote_script="/root/gao-release-${target}.sh"
    checksum=$(sha256sum "$repo/deploy/production_release.sh" | cut -d ' ' -f1)
    scp "${ssh_options[@]}" "$repo/deploy/production_release.sh" "root@${host}:${remote_script}"
    ssh "${ssh_options[@]}" "root@$host" "echo '$checksum  $remote_script' | sha256sum -c - && bash '$remote_script' '$mode' '$target'"
fi
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    printf '\nProduction operation `%s` completed successfully for `%s`.\n' "$mode" "$target" >> "$GITHUB_STEP_SUMMARY"
fi
