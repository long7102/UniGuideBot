"""SQLite catalogue: broad subject areas, not annual admission guarantees."""
import sqlite3
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(tempfile.gettempdir()) / 'uniguidebot-public.db' if os.environ.get('VERCEL') else ROOT / 'universities.db'

@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

def init_db():
    import json
    with connect() as con:
        con.executescript((ROOT / 'sql/schema.sql').read_text(encoding='utf-8'))
        columns={row[1] for row in con.execute('PRAGMA table_info(universities)')}
        metadata_keys=('ownership','institution_type','admission_code','source_url','ministry_source','verified_at','verification_status','field_note','field_source','ownership_source','ownership_note')
        for key in metadata_keys:
            if key not in columns:
                con.execute(f'ALTER TABLE universities ADD COLUMN {key} TEXT NOT NULL DEFAULT ""')
        # Add missing catalogue records even to an existing installation; preserve edits.
        for row in json.loads((ROOT / 'sql/catalogue.json').read_text(encoding='utf-8')):
            con.execute('INSERT OR IGNORE INTO universities(name,short_name,city,region,website,description) VALUES(?,?,?,?,?,?)', tuple(row[k] for k in ('name','short_name','city','region','website','description')))
            school_id = con.execute('SELECT id FROM universities WHERE short_name=?',(row['short_name'],)).fetchone()[0]
            # Only metadata controlled by the catalogue is synchronized; preserve user edits to names/descriptions.
            con.execute('UPDATE universities SET '+','.join(key+'=?' for key in metadata_keys)+' WHERE id=?', [row.get(key,'') for key in metadata_keys]+[school_id])
            for field in row['fields']:
                con.execute('INSERT OR IGNORE INTO university_fields(university_id,field) VALUES(?,?)',(school_id,field))

def search_universities(region=None, field=None, name=None, limit=24, ownership=None):
    clauses, args = [], []
    if region:
        clauses.append('u.region=?'); args.append(region)
    if field:
        clauses.append('EXISTS(SELECT 1 FROM university_fields f WHERE f.university_id=u.id AND f.field=?)'); args.append(field)
    if name:
        clauses.append('(u.name LIKE ? OR u.short_name LIKE ?)'); args.extend(['%'+name+'%']*2)
    if ownership:
        clauses.append('u.ownership=?'); args.append(ownership)
    query = 'SELECT u.* FROM universities u' + (' WHERE '+ ' AND '.join(clauses) if clauses else '') + ' ORDER BY u.id LIMIT ?'
    with connect() as con:
        rows = [dict(r) for r in con.execute(query, args+[limit])]
        for row in rows:
            row['fields'] = [r[0] for r in con.execute('SELECT field FROM university_fields WHERE university_id=?',(row['id'],))]
        from admissions import attach_summaries
    return attach_summaries(rows)

def get_stats():
    with connect() as con:
        return {'universities':con.execute('SELECT COUNT(*) FROM universities').fetchone()[0], 'fields':con.execute('SELECT COUNT(DISTINCT field) FROM university_fields').fetchone()[0], 'regions':con.execute('SELECT COUNT(DISTINCT region) FROM universities').fetchone()[0]}

def catalogue_stats():
    result=get_stats()
    with connect() as con:
        result['north']=con.execute("SELECT COUNT(*) FROM universities WHERE region='bac'").fetchone()[0]
        result['north_private']=con.execute("SELECT COUNT(*) FROM universities WHERE region='bac' AND ownership='tu_thuc'").fetchone()[0]
    return result
