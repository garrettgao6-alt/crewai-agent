"""Online snapshot, SQLite backup API, verified archive; never stops services."""
import fcntl,hashlib,json,os,shutil,sqlite3,sys,tarfile,tempfile
from pathlib import Path
from dotenv import dotenv_values

EXCLUDED={'.git','venv','.venv','__pycache__','.pytest_cache','node_modules'}
def snapshot_tree(source,destination):
    source=Path(source)
    if source.is_file():
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination);return
    destination.mkdir(parents=True,exist_ok=True)
    databases=[]
    for file in sorted(source.rglob('*')):
        relative=file.relative_to(source)
        if any(part in EXCLUDED for part in relative.parts) or file.is_symlink() or file.name.endswith(('-wal','-shm')) or file.name=='.snapshot.lock':continue
        target=destination/relative
        if file.is_dir():target.mkdir(parents=True,exist_ok=True);continue
        if not file.is_file():continue
        target.parent.mkdir(parents=True,exist_ok=True)
        with file.open('rb') as handle:header=handle.read(16)
        if header==b'SQLite format 3\x00':databases.append((file,target))
        else:shutil.copy2(file,target)
    # Child records before owners also preserves references during the one-time
    # migration from releases which did not have the shared snapshot barrier.
    order={'reports.db':0,'projects.db':1,'users.db':2}
    for file,target in sorted(databases,key=lambda pair:order.get(pair[0].name,-1)):
        src=sqlite3.connect(f'file:{file}?mode=ro',uri=True,timeout=30);dst=sqlite3.connect(target)
        try:
            src.backup(dst,pages=256,sleep=0.05)
            assert dst.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        finally:src.close();dst.close()

def backup(app,backup_dir):
    app=Path(app).resolve();backup_dir=Path(backup_dir).resolve();env=dotenv_values(app/'.env')
    extras=[]
    for key in ('NCC_DOCUMENT_ROOT','CHROMA_DB_PATH','COPILOT_MEMORY_DB'):
        value=env.get(key)
        if value:
            path=Path(value).expanduser();path=(app/path).resolve() if not path.is_absolute() else path.resolve()
            if path.exists() and not path.is_relative_to(app):extras.append(path)
    for path in (Path('/etc/nginx/sites-available/gaointelligence'),Path('/var/www/gao-public'),Path('/etc/gaointelligence/operations.env')):
        if path.exists():extras.append(path)
    with tempfile.TemporaryDirectory(prefix='snapshot-',dir=backup_dir) as temporary:
        staging=Path(temporary)
        with (app/'.snapshot.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            snapshot_tree(app,staging/'crewai-agent')
            for index,path in enumerate(dict.fromkeys(extras)):snapshot_tree(path,staging/'external'/str(index)/path.name)
            # Validate owner relationships before accepting the snapshot.
            users=staging/'crewai-agent/users.db';projects=staging/'crewai-agent/projects.db';reports=staging/'crewai-agent/reports.db'
            if users.exists() and projects.exists():
                with sqlite3.connect(users) as c:owners={r[0] for r in c.execute('SELECT id FROM users')}
                with sqlite3.connect(projects) as c:owned={r[0]:r[1] for r in c.execute('SELECT id,user_id FROM projects')}
                assert all(owner in owners for owner in owned.values()),'Snapshot has an orphan project; retry backup'
                if reports.exists():
                    with sqlite3.connect(reports) as c:
                        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                        if 'reports' in tables:assert all(owned.get(project)==owner for owner,project in c.execute('SELECT user_id,project_id FROM reports')),'Snapshot has an orphan report; retry backup'
            fcntl.flock(lock,fcntl.LOCK_UN)
        archive=backup_dir/'application-and-data.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for item in staging.iterdir():tar.add(item,arcname=item.name)
        # Extract and integrity-check the archive in an isolated temporary root.
        with tempfile.TemporaryDirectory(prefix='restore-check-',dir=backup_dir) as restored:
            with tarfile.open(archive,'r:gz') as tar:
                for member in tar.getmembers():
                    if not (Path(restored)/member.name).resolve().is_relative_to(Path(restored).resolve()):raise RuntimeError('Unsafe backup member')
                tar.extractall(restored,filter='data')
            assert (Path(restored)/'crewai-agent/streamlit_app.py').is_file()
            for file in Path(restored).rglob('*'):
                if file.is_file():
                    with file.open('rb') as handle:header=handle.read(16)
                    if header==b'SQLite format 3\x00':
                        connection=sqlite3.connect(f'file:{file}?mode=ro',uri=True)
                        try:assert connection.execute('PRAGMA quick_check').fetchone()[0]=='ok'
                        finally:connection.close()
        digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
        manifest={'archive':archive.name,'sha256':digest,'external_paths':[str(p) for p in extras],'online':True,'restore_integrity_checked':True}
        (backup_dir/'manifest.json').write_text(json.dumps(manifest,indent=2))
        print('BACKUP_VERIFIED',backup_dir,'sha256='+digest,flush=True)
    # Optional operator-authorized off-site destination. No credentials in args/logs.
    try:from .operations import CONFIG, configuration, offsite_copy
    except ImportError:from operations import CONFIG, configuration, offsite_copy
    if CONFIG.exists() and configuration().get('RESTIC_REPOSITORY'):
        offsite_copy(backup_dir)
        return
    remote=os.getenv('GAO_BACKUP_REMOTE') or env.get('GAO_BACKUP_REMOTE')
    if remote:
        import subprocess
        subprocess.run(['rclone','copy',str(backup_dir),remote.rstrip('/')+'/'+backup_dir.name,'--quiet'],check=True)
        subprocess.run(['rclone','check',str(backup_dir),remote.rstrip('/')+'/'+backup_dir.name,'--one-way','--quiet'],check=True)
        print('OFFSITE_BACKUP_VERIFIED',flush=True)
    else:print('OFFSITE_BACKUP_NOT_CONFIGURED',flush=True)

if __name__=='__main__':backup(*sys.argv[1:3])
