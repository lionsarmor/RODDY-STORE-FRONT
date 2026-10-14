"""Save verified paid keycap orders on the owner's droplet for direct transfer."""
import json
import os
from pathlib import Path
import secrets
import shutil
import threading
import time
from .keycaps import packet


class OrderPackets:
    def __init__(self, connect, directory):
        self.connect, self.directory = connect, Path(directory)
        self.lock = threading.Lock()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS keycap_packets (
              session TEXT PRIMARY KEY REFERENCES orders(session), state TEXT NOT NULL DEFAULT 'queued',
              saved INTEGER, error TEXT NOT NULL DEFAULT ''
            )''')

    def enqueue(self, db, session):
        db.execute('INSERT OR IGNORE INTO keycap_packets(session) VALUES(?)', (session,))

    def info(self, session):
        with self.connect() as db:
            row = db.execute('SELECT state,saved,error FROM keycap_packets WHERE session=?', (session,)).fetchone()
        return dict(row) if row else None

    def process(self, order):
        if not self.lock.acquire(blocking=False):
            return
        temp = None
        try:
            with self.connect() as db:
                row = db.execute('SELECT * FROM keycap_packets WHERE session=?', (order['session'],)).fetchone()
                current = db.execute('SELECT paid FROM orders WHERE session=?', (order['session'],)).fetchone()
            if not row or not current['paid']:
                return
            destination = self.directory / ('RODDY-'+order['request_id'])
            if row['state'] == 'ready' and destination.is_dir():
                return
            if not destination.exists():
                temp = self.directory / ('.preparing-'+secrets.token_hex(16))
                temp.mkdir(mode=0o700)
                _, files = packet(order)
                for filename, content in files:
                    fd = os.open(temp / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, 'wb') as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                # Only complete folders are visible to the laptop sync command.
                temp.rename(destination)
                temp = None
            with self.connect() as db:
                db.execute("UPDATE keycap_packets SET state='ready',saved=?,error='' WHERE session=?", (int(time.time()),order['session']))
        except OSError:
            with self.connect() as db:
                db.execute("UPDATE keycap_packets SET state='queued',error='Could not save the packet on disk. Check droplet disk space and directory permissions. Admin ZIP download remains available.' WHERE session=?", (order['session'],))
        finally:
            if temp is not None:
                shutil.rmtree(temp, ignore_errors=True)
            self.lock.release()
