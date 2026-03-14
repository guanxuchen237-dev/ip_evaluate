import pymysql
import json
from data_manager import ZONGHENG_CONFIG

data = {"zongheng_book_ranks": [], "ip_ai_evaluation": []}

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute("SELECT * FROM zongheng_book_ranks WHERE title = '齐天' ORDER BY year DESC, month DESC LIMIT 3")
    data["zongheng_book_ranks"] = cur.fetchall()

    cur.execute("SELECT * FROM ip_ai_evaluation WHERE title = '齐天'")
    data["ip_ai_evaluation"] = cur.fetchall()

from data_manager import QIDIAN_CONFIG
try:
    conn2 = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn2.cursor() as cur2:
         cur2.execute("SELECT * FROM novel_monthly_stats WHERE title = '齐天' ORDER BY year DESC, month DESC LIMIT 3")
         data["novel_monthly_stats"] = cur2.fetchall()
    conn2.close()
except:
    pass

conn.close()

with open('qitian_data_utf8.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, default=str)
