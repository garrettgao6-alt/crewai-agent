"""One bounded parser process per application; no upload can run unbounded in the web process."""
from contextlib import contextmanager
from pathlib import Path
import fcntl,json,os,subprocess,sys,tempfile

@contextmanager
def parser_slot():
    lock=Path(__file__).resolve().parents[1]/'.file-parser.lock'
    with lock.open('a+b') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('The file processor is busy. Retry shortly.') from None
        yield

def run(mode,path,name=''):
    app=Path(__file__).resolve().parents[1]
    env={k:v for k,v in os.environ.items() if not any(x in k for x in ('OPENAI','GMAIL','SMTP','RESTIC','AWS_','PASSWORD','SECRET','TOKEN'))}
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(app))
    with parser_slot():
        try:
            proc=subprocess.run([sys.executable,'-m','core.file_worker'],input=json.dumps({'mode':mode,'path':str(Path(path).resolve()),'name':name}),env=env,cwd=app,text=True,capture_output=True,timeout=40)
        except subprocess.TimeoutExpired:raise ValueError('File processing exceeded 40 seconds. Split or simplify the file.') from None
    if proc.returncode or len(proc.stdout.encode())>1024*1024:raise ValueError('The file exceeded parser resource limits or could not be processed.')
    try:result=json.loads(proc.stdout)
    except ValueError:raise ValueError('The file could not be processed safely.') from None
    if result.get('error'):raise ValueError(result['error'])
    return result['result']

def document_pages(name,data):
    with tempfile.TemporaryDirectory(prefix='gao-document-') as temp:
        path=Path(temp)/'source';path.write_bytes(data)
        return run('document',path,name)
