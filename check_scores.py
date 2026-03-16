import pymysql, pandas as pd
import sys; sys.path.insert(0, 'd:/ip-lumina-main/integrated_system/backend')
from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG

conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute('SELECT title, author, IP_Score, monthly_tickets_on_list, recommendation_count FROM novel_monthly_stats ORDER BY IP_Score DESC LIMIT 10')
    qd_top = cur.fetchall()
conn.close()

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute('SELECT title, author, IP_Score, monthly_ticket, total_rec FROM zongheng_book_ranks ORDER BY IP_Score DESC LIMIT 10')
    zh_top = cur.fetchall()
conn.close()

print('=== Qidian Top 10 by IP_Score ===')
for b in qd_top: print(f"{b['title']} - IP_Score: {b['IP_Score']}, Tickets: {b['monthly_tickets_on_list']}, Recs: {b['recommendation_count']}")

print('\n=== Zongheng Top 10 by IP_Score ===')
for b in zh_top: print(f"{b['title']} - IP_Score: {b['IP_Score']}, Tickets: {b['monthly_ticket']}, Recs: {b['total_rec']}")
