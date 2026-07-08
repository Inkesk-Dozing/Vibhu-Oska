import sqlite3, pathlib

root = pathlib.Path(r'c:\Users\USER\Desktop\Extras\.i-oska\Vibhu-Oska')
dbs = list(root.rglob('*.db'))
print('DBs found:', [str(d.relative_to(root)) for d in dbs])

for db in dbs:
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'\n{db.name}: tables={tables}')
        for tbl in tables:
            if 'cache' in tbl.lower():
                cur.execute(f'SELECT COUNT(*) FROM {tbl}')
                cnt = cur.fetchone()[0]
                print(f'  {tbl}: {cnt} rows')
                cur.execute(f'SELECT * FROM {tbl} LIMIT 5')
                cols = [d[0] for d in cur.description]
                print(f'  cols: {cols}')
                for row in cur.fetchall():
                    print(f'  ROW: {str(row)[:120]}')
        conn.close()
    except Exception as e:
        print(f'  error: {e}')
