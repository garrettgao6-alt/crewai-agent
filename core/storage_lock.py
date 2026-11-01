"""Short shared write/snapshot barrier across API and Streamlit processes."""
from contextlib import contextmanager
from pathlib import Path
from functools import wraps
import fcntl,sqlite3,os

def lock_path():return Path(os.getenv('GAO_SNAPSHOT_LOCK',str(Path(__file__).resolve().parents[1]/'.snapshot.lock')))

@contextmanager
def snapshot_guard():
    with lock_path().open('a+b') as handle:
        fcntl.flock(handle,fcntl.LOCK_SH)
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)

class Connection(sqlite3.Connection):
    def __init__(self,*args,**kwargs):
        self._snapshot_handle=lock_path().open('a+b')
        fcntl.flock(self._snapshot_handle,fcntl.LOCK_SH)
        try:super().__init__(*args,**kwargs)
        except Exception:self._snapshot_handle.close();raise
    def close(self):
        try:super().close()
        finally:
            if not self._snapshot_handle.closed:self._snapshot_handle.close()
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

def snapshot_writer(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        with snapshot_guard():return function(*args,**kwargs)
    return wrapped
