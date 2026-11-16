"""Install the verified fresh index in the product's actual Windows data folder."""
import json
import os
from pathlib import Path
import shutil
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'outputs/review-20261114'
SOURCE=WORK/'measured-library'
TARGET=Path(os.environ['APPDATA'])/'app.frameatlas.desktop'
OLD=ROOT/'data/desktop-acceptance'
data=json.loads((WORK/'index-ten-videos.json').read_text(encoding='utf-8'))
assert data['summary']['ready']==10 and data['summary']['frames']==5480
with sqlite3.connect(SOURCE/'library.sqlite3') as src:
    assert src.execute('SELECT COUNT(*) FROM frames').fetchone()[0]==5480
    assert src.execute('SELECT COUNT(*) FROM videos WHERE status="ready"').fetchone()[0]==10
    thumbs=[r[0] for r in src.execute('SELECT thumb FROM frames')]
    for sub in ('thumbnails','details'):
        assert all((SOURCE/sub/name).is_file() for name in thumbs)
with sqlite3.connect(TARGET/'library.sqlite3') as dest:
    if dest.execute('SELECT COUNT(*) FROM videos').fetchone()[0]:
        raise RuntimeError('Native library is no longer empty; preserve it and resolve merge first')
    with sqlite3.connect(WORK/'native-original.sqlite3') as backup:dest.backup(backup)
for sub in ('thumbnails','details','sampling'):
    shutil.copytree(SOURCE/sub,TARGET/sub,dirs_exist_ok=True)
with sqlite3.connect(SOURCE/'library.sqlite3') as src,sqlite3.connect(TARGET/'library.sqlite3') as dest:
    src.backup(dest)
    dest.execute('PRAGMA foreign_keys=ON')
    dest.execute('ATTACH DATABASE ? AS old',(str(OLD/'library.sqlite3'),))
    for table in ('folders','history','moments'):
        dest.execute(f'INSERT OR IGNORE INTO main.{table} SELECT * FROM old.{table}')
    assert not dest.execute('PRAGMA foreign_key_check').fetchall()
    dest.commit()
    dest.execute('PRAGMA wal_checkpoint(TRUNCATE)')
print('Native library installed:',TARGET,'10 videos / 5480 frames',flush=True)
