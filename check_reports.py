import pymysql
import json

AUTH_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'ip_lumina_auth',
    'cursorclass': pymysql.cursors.DictCursor
}

try:
    conn = pymysql.connect(**AUTH_CONFIG)
    with conn.cursor() as cur:
        cur.execute('''
            SELECT id, book_title, score, LEFT(markdown_report, 300) as report_preview, created_at 
            FROM ip_audit_logs 
            WHERE markdown_report IS NOT NULL 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        rows = cur.fetchall()
        for r in rows:
            r['created_at'] = str(r['created_at'])
            print(json.dumps(r, ensure_ascii=False, indent=2))
            print('-' * 40)
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
