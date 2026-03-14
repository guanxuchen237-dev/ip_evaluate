import pymysql, warnings, json
warnings.filterwarnings('ignore')

ZH = {'host':'localhost','port':3306,'user':'root','password':'root','database':'zongheng_analysis_v8','charset':'utf8mb4'}
QD = {'host':'localhost','port':3306,'user':'root','password':'root','database':'qidian_data','charset':'utf8mb4'}

result = {}

# ZONGHENG
c = pymysql.connect(**ZH, cursorclass=pymysql.cursors.DictCursor)
cur = c.cursor()
cur.execute('SHOW TABLES')
tables = [r[list(r.keys())[0]] for r in cur.fetchall()]
result['zh_tables'] = {}
for t in tables:
    cur.execute(f'SHOW COLUMNS FROM `{t}`')
    cols = [r['Field'] for r in cur.fetchall()]
    cur.execute(f'SELECT COUNT(*) as c FROM `{t}`')
    cnt = cur.fetchone()['c']
    result['zh_tables'][t] = {'columns': cols, 'rows': cnt}

# Sample comment data
cur.execute('SELECT * FROM zongheng_book_comments LIMIT 2')
rows = cur.fetchall()
result['zh_comment_samples'] = [{k: str(v) for k, v in r.items()} for r in rows]

# ZH top10 monthly tickets from realtime
cur.execute("SELECT title, monthly_tickets, crawl_time FROM zongheng_realtime_tracking ORDER BY monthly_tickets DESC LIMIT 10")
result['zh_top10'] = [{k: str(v) for k, v in r.items()} for r in cur.fetchall()]
c.close()

# QIDIAN
c2 = pymysql.connect(**QD, cursorclass=pymysql.cursors.DictCursor)
cur2 = c2.cursor()
cur2.execute('SHOW TABLES')
tables2 = [r[list(r.keys())[0]] for r in cur2.fetchall()]
result['qd_tables'] = {}
for t in tables2:
    cur2.execute(f'SHOW COLUMNS FROM `{t}`')
    cols = [r['Field'] for r in cur2.fetchall()]
    cur2.execute(f'SELECT COUNT(*) as c FROM `{t}`')
    cnt = cur2.fetchone()['c']
    result['qd_tables'][t] = {'columns': cols, 'rows': cnt}

cur2.execute("SELECT title, monthly_tickets, crawl_time FROM novel_realtime_tracking ORDER BY monthly_tickets DESC LIMIT 10")
result['qd_top10'] = [{k: str(v) for k, v in r.items()} for r in cur2.fetchall()]
c2.close()

with open('d:/ip-lumina-main/integrated_system/backend/db_schema.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("DONE - saved to db_schema.json")
