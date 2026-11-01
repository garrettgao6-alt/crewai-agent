"""Bounded local parsers. Fixed code only; no provider credentials or external actions."""
import json,os,sys
from pathlib import Path

def main():
    job=json.loads(sys.stdin.read(4096));mode=job['mode'];path=Path(job['path'])
    try:
        if sys.platform.startswith('linux'):
            import resource
            resource.setrlimit(resource.RLIMIT_CPU,(30,30))
            resource.setrlimit(resource.RLIMIT_AS,(1200*1024**2,1200*1024**2))
        if path.stat().st_size>50*1024**2:raise ValueError('File exceeds the 50 MB limit.')
        if mode=='ifc':
            from core.bim_checks import inspect_file
            result=inspect_file(path)
        elif mode=='document':
            from core.document_pipeline import native_pages
            result=native_pages(job['name'],path.read_bytes())
        else:raise ValueError('Unsupported processing mode.')
        print(json.dumps({'result':result},ensure_ascii=False,allow_nan=False))
    except ValueError as exc:print(json.dumps({'error':str(exc)[:300]}))
    except Exception:print(json.dumps({'error':'File parsing failed. Check format, encryption and file validity.'}))
if __name__=='__main__':main()
