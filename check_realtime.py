import pymysql

# 查看所有数据库
conn = pymysql.connect(host='localhost', user='root', password='root', cursorclass=pymysql.cursors.DictCursor)

with conn.cursor() as cur:
    cur.execute('SHOW DATABASES')
    dbs = cur.fetchall()
    print('所有数据库:')
    for db in dbs:
        name = db['Database']
        print(f'  - {name}')

conn.close()

# 查询起点历史数据库
print('\n=== 历史数据库 qidian_data ===')
conn1 = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', cursorclass=pymysql.cursors.DictCursor)
with conn1.cursor() as cur:
    cur.execute('SHOW TABLES')
    tables = cur.fetchall()
    print('表:')
    for t in tables:
        print(f'  - {list(t.values())[0]}')
    
    # 查看 novel_realtime_tracking 表结构
    print('\n--- novel_realtime_tracking 表结构 ---')
    cur.execute('DESCRIBE novel_realtime_tracking')
    cols = cur.fetchall()
    for col in cols:
        print(f'  {col["Field"]} - {col["Type"]}')
    
    # 查看最新数据
    print('\n--- novel_realtime_tracking 最新数据 ---')
    cur.execute('SELECT * FROM novel_realtime_tracking ORDER BY id DESC LIMIT 5')
    rows = cur.fetchall()
    for row in rows:
        print(f'  {row}')
    
    # 查看捞尸人实时数据
    print('\n--- 捞尸人实时数据 ---')
    cur.execute("""
        SELECT * FROM novel_realtime_tracking 
        WHERE title LIKE '%捞尸人%' 
        ORDER BY id DESC LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f'  {row}')
    else:
        print('  无数据')

conn1.close()

# 查询 novel_insights 数据库（可能是实时数据库）
print('\n=== 实时数据库 novel_insights ===')
try:
    conn3 = pymysql.connect(host='localhost', user='root', password='root', database='novel_insights', cursorclass=pymysql.cursors.DictCursor)
    with conn3.cursor() as cur:
        cur.execute('SHOW TABLES')
        tables = cur.fetchall()
        print('表:')
        for t in tables:
            print(f'  - {list(t.values())[0]}')
    conn3.close()
except Exception as e:
    print(f'无法连接: {e}')
