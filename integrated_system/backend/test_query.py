import pymysql
import sys
sys.path.append('d:/ip-lumina-main/integrated_system/backend')
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

c.execute("SELECT MAX(monthly_ticket) as tkts, MAX(total_rec) as r_c, MAX(word_count) as wc FROM zongheng_book_ranks WHERE title LIKE '%无敌天命%'")
print("zongheng_book_ranks:", c.fetchall())

c.execute("SELECT MAX(monthly_tickets) as tkts FROM zongheng_realtime_tracking WHERE title LIKE '%无敌天命%'")
print("zongheng_realtime_tracking:", c.fetchall())

conn.close()
