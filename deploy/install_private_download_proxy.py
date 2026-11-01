"""Add only the authorized private-download route; preserve and validate existing Nginx configuration."""
from pathlib import Path
import datetime,shutil,subprocess
SITE=Path('/etc/nginx/sites-available/gaointelligence')
LOG=Path('/etc/nginx/conf.d/gao-private-download-log.conf')
ROUTE='''    location ^~ /private-download/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        access_log /var/log/nginx/gao-private-download.log gao_private_download;
    }

'''
def install():
    source=SITE.read_text()
    if 'location ^~ /private-download/' in source:return
    if source.count('    location / {')!=1:raise RuntimeError('Unexpected site configuration; no changes made.')
    backup=Path('/root/gao-backups')/('proxy-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True,mode=0o700);shutil.copy2(SITE,backup/'site.conf')
    old_log=LOG.read_bytes() if LOG.exists() else None
    if old_log is not None:(backup/'log.conf').write_bytes(old_log)
    try:
        LOG.write_text('log_format gao_private_download \'$remote_addr [$time_local] "GET /private-download/[redacted]" $status $body_bytes_sent\';\n')
        SITE.write_text(source.replace('    location / {',ROUTE+'    location / {',1))
        subprocess.run(['nginx','-t'],check=True)
        subprocess.run(['systemctl','reload','nginx'],check=True)
    except Exception:
        shutil.copy2(backup/'site.conf',SITE)
        if old_log is None:LOG.unlink(missing_ok=True)
        else:LOG.write_bytes(old_log)
        subprocess.run(['nginx','-t'],check=True);subprocess.run(['systemctl','reload','nginx'],check=True)
        raise
    print('PRIVATE_DOWNLOAD_PROXY_VERIFIED backup='+str(backup))
if __name__=='__main__':install()
