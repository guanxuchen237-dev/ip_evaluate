import sys
sys.path.append('d:/ip-lumina-main/integrated_system')
from backend.data_manager import QIDIAN_CONFIG
import pymysql
import json

conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
out_data = {}
with conn.cursor() as cur:
    cur.execute("SELECT MAX(year * 100 + month) as max_period FROM novel_monthly_stats")
    out_data['max_period'] = cur.fetchone()['max_period']
    
    cur.execute("SELECT year, month, monthly_tickets_on_list, rank_on_list FROM novel_monthly_stats WHERE title='旧日之箓' ORDER BY year DESC, month DESC LIMIT 5")
    out_data['history'] = cur.fetchall()
conn.close()

with open('d:/ip-lumina-main/integrated_system/backend/test_out.json', 'w') as f:
    json.dump(out_data, f)
