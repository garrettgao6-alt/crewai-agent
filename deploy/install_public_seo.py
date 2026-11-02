"""Back up and atomically install public guides; restore on any failed check."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from public_site import build
SITE=Path('/etc/nginx/sites-available/gaointelligence')
MAP=Path('/etc/nginx/conf.d/gao-search-robots.conf')
SNIPPET=Path('/etc/nginx/snippets/gao-public-seo.conf')
PUBLIC=Path('/var/www/gao-seo')
MARKER='    # Gao public search guides\n'
MAP_TEXT='''map $uri $gao_search_robots {
    default "noindex, nofollow, noarchive";
    ~^/discover(?:/|$) "";
    ~^/seo-assets/ "";
    /robots.txt "";
    /sitemap.xml "";
    /mail-privacy "";
}
'''
SNIPPET_TEXT='''# Generated public-only files; never alias application data directories.
location = /discover { return 301 https://www.gaointelligence.com/discover/; }
location ^~ /discover/ {
    if ($host != "www.gaointelligence.com") { return 301 https://www.gaointelligence.com$request_uri; }
    root /var/www/gao-seo/current;
    index index.html;
    try_files $uri $uri/ =404;
    charset utf-8;
}
location ^~ /seo-assets/ {
    root /var/www/gao-seo/current;
    try_files $uri =404;
    expires 1h;
}
location = /robots.txt {
    if ($host != "www.gaointelligence.com") { return 301 https://www.gaointelligence.com$request_uri; }
    root /var/www/gao-seo/current;
    try_files $uri =404;
    types { }
    default_type text/plain;
}
location = /sitemap.xml {
    if ($host != "www.gaointelligence.com") { return 301 https://www.gaointelligence.com$request_uri; }
    root /var/www/gao-seo/current;
    try_files $uri =404;
    types { }
    default_type application/xml;
}
'''

def site_config(text):
    if MARKER in text:
        if text.count(MARKER)!=1 or text.count('include /etc/nginx/snippets/gao-public-seo.conf;')!=1:
            raise ValueError('Ambiguous public guide configuration')
        return text
    needle='    location / {'
    if text.count(needle)!=1:raise ValueError('Expected one existing workspace location; refusing ambiguous change')
    if '$gao_search_robots' in text:raise ValueError('Unexpected existing search policy')
    return text.replace(needle,MARKER+'    add_header X-Robots-Tag $gao_search_robots always;\n    include /etc/nginx/snippets/gao-public-seo.conf;\n\n'+needle,1)

def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.gao-tmp')
    temp.write_bytes(data);temp.chmod(0o644);os.replace(temp,path)

def point_to(target):
    link=PUBLIC/'current';temp=PUBLIC/'current.gao-tmp'
    if temp.is_symlink():temp.unlink()
    temp.symlink_to(target);os.replace(temp,link)

def reload_nginx():
    subprocess.run(['nginx','-t'],check=True)
    subprocess.run(['systemctl','reload','nginx'],check=True)

def save_state(backup):
    state=backup/'public-seo-state';state.mkdir(mode=0o700)
    files=[]
    for index,path in enumerate((SITE,MAP,SNIPPET)):
        existed=path.exists()
        files.append({'path':str(path),'existed':existed,'backup':str(index)})
        if existed:shutil.copy2(path,state/str(index))
    link=PUBLIC/'current'
    if link.exists() and not link.is_symlink():raise ValueError('Public current path is not a symlink')
    manifest={'files':files,'link':os.readlink(link) if link.is_symlink() else None}
    (state/'state.json').write_text(json.dumps(manifest))
    # Keep a standalone recovery executable even if source rollback removes this new file.
    shutil.copy2(__file__,state/'restore.py')
    shutil.copy2(ROOT/'public_site.py',state/'public_site.py')
    return state

def restore(backup):
    state=backup/'public-seo-state'
    if not (state/'state.json').exists():return
    manifest=json.loads((state/'state.json').read_text())
    for item in manifest['files']:
        path=Path(item['path'])
        if item['existed']:atomic_write(path,(state/item['backup']).read_bytes())
        else:path.unlink(missing_ok=True)
    if manifest['link'] is None:(PUBLIC/'current').unlink(missing_ok=True)
    else:point_to(manifest['link'])
    reload_nginx()

def verify_public_ready(timeout=20):
    # Reload completes before new Nginx workers have replaced old workers.
    deadline=time.monotonic()+timeout
    failure='No response'
    while True:
        try:
            for route,expected in (('/discover/','Construction AI'),('/robots.txt','User-agent: *'),('/sitemap.xml','<urlset')):
                with urllib.request.urlopen('https://www.gaointelligence.com'+route,timeout=5) as response:
                    body=response.read().decode()
                    if response.status!=200 or expected not in body or 'noindex' in response.headers.get('X-Robots-Tag',''):
                        raise RuntimeError('Public readiness failed at '+route+' status='+str(response.status))
            return
        except (OSError,RuntimeError) as exc:
            failure=type(exc).__name__+': '+str(exc)
        if time.monotonic()>=deadline:raise RuntimeError(failure)
        time.sleep(0.5)


def install(backup):
    new_config=site_config(SITE.read_text())
    state=save_state(backup)
    try:
        PUBLIC.mkdir(parents=True,exist_ok=True);PUBLIC.chmod(0o755)
        releases=PUBLIC/'releases';releases.mkdir(exist_ok=True);releases.chmod(0o755)
        with tempfile.TemporaryDirectory(dir=releases) as tmp:
            tree=build(tmp)
            digest=hashlib.sha256()
            for file in sorted(tree.rglob('*')):
                file.chmod(0o755 if file.is_dir() else 0o644)
                if file.is_file():digest.update(str(file.relative_to(tree)).encode()+b'\0'+file.read_bytes())
            tree.chmod(0o755)
            release=releases/digest.hexdigest()[:20]
            if not release.exists():shutil.copytree(tree,release)
        point_to(release)
        atomic_write(MAP,MAP_TEXT.encode());atomic_write(SNIPPET,SNIPPET_TEXT.encode());atomic_write(SITE,new_config.encode())
        reload_nginx()
        verify_public_ready()
        print('Public search guides installed; prior configuration retained at '+str(state))
    except BaseException:
        restore(backup)
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('backup_dir',type=Path);parser.add_argument('--restore',action='store_true');args=parser.parse_args()
    (restore if args.restore else install)(args.backup_dir)
