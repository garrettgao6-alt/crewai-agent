#!/usr/bin/env bash
set -euo pipefail
umask 077
mode="${1:?backup or deploy}"
target="${2:-}"
app=/root/crewai-agent
cd "$app"
exec 9>/root/gao-release.lock
flock -n 9 || { echo 'Another release is running'; exit 1; }
old_commit=$(cat .release_sha 2>/dev/null || sha256sum streamlit_app.py | cut -c1-12)
backup_dir="/root/gao-backups/$(date -u +%Y%m%dT%H%M%SZ)-${old_commit:0:12}"
mkdir -p "$backup_dir"
chmod 700 /root/gao-backups "$backup_dir"
printf '%s\n' "$old_commit" > "$backup_dir/previous-version"
systemctl cat crewai > "$backup_dir/service-units.txt"
systemctl cat garrett-api >> "$backup_dir/service-units.txt" 2>/dev/null || true
for service in crewai garrett-api; do
    file="/etc/systemd/system/${service}.service.d/90-gao-release.conf"
    if [ -f "$file" ]; then cp "$file" "$backup_dir/${service}.override"; fi
done
api_unit_existed=false
if [ -f /etc/systemd/system/garrett-api.service ]; then
    api_unit_existed=true
    cp /etc/systemd/system/garrett-api.service "$backup_dir/api-unit"
fi
active_services=()
for service in crewai garrett-api garrett-streamlit; do
    if systemctl is-active --quiet "$service"; then active_services+=("$service"); fi
done
webhook_active=false
if systemctl is-active --quiet webhook; then webhook_active=true; fi
systemctl stop webhook 2>/dev/null || true
stopped=false
switched=false
success=false
restart_previous() {
    if [ "$switched" = true ]; then
        systemctl stop crewai garrett-api 2>/dev/null || true
        python3 - "$app" "$backup_dir" <<'PY'
import json,shutil,sys
from pathlib import Path
app,backup=map(Path,sys.argv[1:])
for entry in json.loads((backup/'source-changes.json').read_text()):
    destination=app/entry['path']
    if entry['existed']:
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(backup/'old-source'/entry['path'],destination)
    else:
        destination.unlink(missing_ok=True)
PY
        for service in crewai garrett-api; do
            file="/etc/systemd/system/${service}.service.d/90-gao-release.conf"
            if [ -f "$backup_dir/${service}.override" ]; then cp "$backup_dir/${service}.override" "$file"; else rm -f "$file"; fi
        done
        if [ "$api_unit_existed" = false ]; then
            systemctl disable garrett-api 2>/dev/null || true
            rm -f /etc/systemd/system/garrett-api.service
        else
            cp "$backup_dir/api-unit" /etc/systemd/system/garrett-api.service
        fi
        systemctl daemon-reload
    fi
    if [ "${#active_services[@]}" -gt 0 ]; then systemctl start "${active_services[@]}"; fi
}
finish() {
    code=$?
    if [ "$success" != true ]; then
        echo 'Release failed; preserving data and restoring previous code/runtime.'
        if [ "$stopped" = true ] || [ "$switched" = true ]; then restart_previous || true; fi
        if [ "$webhook_active" = true ]; then systemctl start webhook || true; fi
    fi
    exit "$code"
}
trap finish EXIT
if [ "${#active_services[@]}" -gt 0 ]; then systemctl stop "${active_services[@]}"; fi
stopped=true
"$app/venv/bin/python" - "$app" "$backup_dir" <<'PY'
import hashlib,json,os,sqlite3,sys,tarfile
from pathlib import Path
from dotenv import dotenv_values
app,backup=map(Path,sys.argv[1:])
env={**dotenv_values(app/'.env'),**os.environ}
external=[]
for key in ('NCC_DOCUMENT_ROOT','CHROMA_DB_PATH','COPILOT_MEMORY_DB'):
    value=env.get(key)
    if value:
        path=Path(value).expanduser()
        path=(app/path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(app) and path.exists(): external.append(path)
for database in app.glob('*.db'):
    connection=sqlite3.connect(f'file:{database}?mode=ro',uri=True)
    try:
        if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok': raise RuntimeError('Database integrity check failed')
    finally: connection.close()
excluded={'.git','venv','.venv','__pycache__','.pytest_cache','node_modules'}
def keep(info):
    return None if any(part in excluded for part in Path(info.name).parts) else info
archive=backup/'application-and-data.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    tar.add(app,arcname='crewai-agent',filter=keep)
    for index,path in enumerate(dict.fromkeys(external)):
        tar.add(path,arcname=f'external/{index}/{path.name}',filter=keep)
with tarfile.open(archive,'r:gz') as tar:
    members=tar.getmembers()
    if not any(member.name.endswith('streamlit_app.py') for member in members): raise RuntimeError('Backup code missing')
    for member in members:
        if member.isfile():
            handle=tar.extractfile(member)
            while handle.read(1024*1024): pass
digest=hashlib.sha256()
with archive.open('rb') as handle:
    for block in iter(lambda:handle.read(1024*1024),b''): digest.update(block)
manifest={'archive':archive.name,'sha256':digest.hexdigest(),'external_paths':[str(p) for p in external],'members':len(members)}
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('BACKUP_VERIFIED',str(backup),'sha256='+manifest['sha256'])
PY
restart_previous
stopped=false
printf '%s\n' "$backup_dir" > /root/gao-latest-verified-backup
if [ "$mode" = backup ]; then
    success=true
    echo 'BACKUP_ONLY_COMPLETE; existing application restarted; webhook paused until release.'
    exit 0
fi
[ "$mode" = deploy ]
[[ "$target" =~ ^[0-9a-f]{40}$ ]]
release="/root/gao-releases/$target"
mkdir -p "$release/source"
curl --fail --location --retry 2 "https://codeload.github.com/garrettgao6-alt/crewai-agent/tar.gz/$target" -o "$release/source.tar.gz"
tar -xzf "$release/source.tar.gz" --strip-components=1 -C "$release/source"
new_runtime="$release/venv"
python3 -m venv "$new_runtime"
# Stage runtime while the old application stays up, without mutating its venv.
"$new_runtime/bin/python" -m pip install -r "$release/source/requirements.txt" > "$backup_dir/dependency-install.log" 2>&1 || { echo 'Dependency installation failed; log retained privately.'; exit 1; }
"$new_runtime/bin/python" -m pip install pytest==8.4.2 'markdown-it-py>=3,<4' >> "$backup_dir/dependency-install.log" 2>&1
"$new_runtime/bin/python" -m compileall -q "$release/source/api.py" "$release/source/core" "$release/source/streamlit_app.py"
# Check the actual configured provider before stopping the current application.
"$new_runtime/bin/python" - "$app/.env" <<'PY'
import os, sys
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv(sys.argv[1])
try:
    client = OpenAI(timeout=20, max_retries=0)
    result = client.embeddings.create(model='text-embedding-3-large', input='Deployment readiness check')
    if not result.data or not result.data[0].embedding:
        raise RuntimeError('Empty embedding response')
    result = client.responses.create(model=os.getenv('OPENAI_REASONING_MODEL', 'gpt-4o-mini'), input='Reply OK.', max_output_tokens=16)
    if not result.output_text:
        raise RuntimeError('Empty model response')
except Exception as exc:
    # Provider exception strings may include credentials; never print them.
    print('PROVIDER_PREFLIGHT_FAILED', type(exc).__name__, 'status='+str(getattr(exc, 'status_code', 'unknown')))
    sys.exit(1)
print('PROVIDER_PREFLIGHT_PASSED')
PY
if [ "$api_unit_existed" = false ] && ss -ltn | grep -qE ':8000[[:space:]]'; then echo 'Port 8000 is already owned by another service; stopping safely.'; exit 1; fi
if [ "${#active_services[@]}" -gt 0 ]; then systemctl stop "${active_services[@]}"; fi
stopped=true
printf '[]' > "$backup_dir/source-changes.json"
switched=true
python3 - "$app" "$release/source" "$backup_dir" <<'PY'
import json,shutil,sys
from pathlib import Path
app,source,backup=map(Path,sys.argv[1:])
changes=[]
for path in sorted(source.rglob('*')):
    rel=path.relative_to(source)
    if not path.is_file() or path.is_symlink() or any(part in {'.git','.github','.agents','.codex','__pycache__'} for part in rel.parts): continue
    if path.suffix in {'.db','.sqlite','.sqlite3'} or rel.name=='.env': continue
    destination=app/rel
    existed=destination.is_file()
    if existed:
        saved=backup/'old-source'/rel
        saved.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(destination,saved)
    changes.append({'path':str(rel),'existed':existed})
    # Journal before mutation so an interrupted copy can be rolled back.
    (backup/'source-changes.json').write_text(json.dumps(changes))
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,destination)
PY
switched=true
for service in crewai garrett-api; do mkdir -p "/etc/systemd/system/${service}.service.d"; done
if [ "$api_unit_existed" = false ]; then
    cat > /etc/systemd/system/garrett-api.service <<EOF
[Unit]
Description=Gao Intelligence project API
After=network.target
[Service]
WorkingDirectory=$app
ExecStart=$new_runtime/bin/uvicorn api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
fi
cat > /etc/systemd/system/crewai.service.d/90-gao-release.conf <<EOF
[Service]
ExecStart=
ExecStart=$new_runtime/bin/streamlit run $app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --client.showErrorDetails none
EOF
cat > /etc/systemd/system/garrett-api.service.d/90-gao-release.conf <<EOF
[Service]
ExecStart=
ExecStart=$new_runtime/bin/uvicorn api:app --host 127.0.0.1 --port 8000
EOF
"$new_runtime/bin/python" - "$app" <<'PYCONF'
import sys
from pathlib import Path
from dotenv import dotenv_values,set_key
app=Path(sys.argv[1])
envfile=app/'.env'
if not dotenv_values(envfile).get('NCC_DOCUMENT_ROOT'):
    root=Path('/srv/gaointelligence/ncc')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    set_key(str(envfile),'NCC_DOCUMENT_ROOT',str(root))
PYCONF
systemctl daemon-reload
systemctl enable garrett-api
systemctl start garrett-api crewai
for attempt in $(seq 1 30); do
    if curl --fail --silent http://127.0.0.1:8000/health >/dev/null && curl --fail --silent http://127.0.0.1:8501/_stcore/health >/dev/null; then break; fi
    sleep 2
done
curl --fail --silent http://127.0.0.1:8000/health >/dev/null
curl --fail --silent http://127.0.0.1:8501/_stcore/health >/dev/null
"$new_runtime/bin/python" deploy/production_verify.py > "$backup_dir/acceptance.log" 2>&1 || { echo 'Production acceptance failed; rolling back. Private log retained.'; test ! -f /root/gao-latest-acceptance.json || cat /root/gao-latest-acceptance.json; exit 1; }
cp /root/gao-latest-acceptance.json "$backup_dir/acceptance.json"
printf '%s\n' "$target" > "$app/.release_sha"
success=true
echo "RELEASE_VERIFIED commit=$target backup=$backup_dir"
cat /root/gao-latest-acceptance.json
