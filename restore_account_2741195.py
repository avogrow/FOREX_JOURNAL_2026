import sqlite3
import os
from pathlib import Path
import pandas as pd

print('cwd', os.getcwd())
print('db_exists', os.path.exists('forex_tracker.db'))
print('xlsx_exists', Path('ReportHistory-2741195.xlsx').exists())

if os.path.exists('forex_tracker.db'):
    conn = sqlite3.connect('forex_tracker.db')
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(trades)")
        print('trades_schema', cur.fetchall())
    except Exception as e:
        print('schema_error', e)
    try:
        cur.execute("SELECT COUNT(*) FROM trades WHERE subscription_key LIKE '%2741195%' OR account_id LIKE '%2741195%'")
        print('trades_count', cur.fetchone()[0])
    except Exception as e:
        print('trades_query_error', e)
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('tables', cur.fetchall())
    except Exception as e:
        print('tables_error', e)
    conn.close()

path = Path('ReportHistory-2741195.xlsx')
if path.exists():
    xl = pd.ExcelFile(path)
    print('sheets', xl.sheet_names)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=None)
        print('first 30 rows:')
        for i, row in df.head(30).iterrows():
            print(i, row.tolist())
        print('---')
        df2 = xl.parse(sheet, nrows=200, header=None)
        print('total_rows', len(df2))
        for i in range(min(15, len(df2))):
            print(i, df2.iloc[i].tolist())
        print('--- done sample ---')
