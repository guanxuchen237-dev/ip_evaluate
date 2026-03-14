import pymysql
from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG

print("--- QiDian Max Tickets (Last 30 Days) ---")
try:
    conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(monthly_tickets) as m FROM novel_realtime_tracking")
        print("QD Max Realtime:", cur.fetchone()['m'])
        cur.execute("SELECT MAX(monthly_ticket) as m FROM novel_monthly_stats")
        print("QD Max Monthly:", cur.fetchone()['m'])
    conn.close()
except Exception as e: print(e)

print("\n--- Zongheng Max Tickets (Last 30 Days) ---")
try:
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(monthly_tickets) as m FROM zongheng_realtime_tracking")
        print("ZH Max Realtime:", cur.fetchone()['m'])
        cur.execute("SELECT MAX(monthly_ticket) as m FROM zongheng_book_ranks")
        print("ZH Max Monthly:", cur.fetchone()['m'])
    conn.close()
except Exception as e: print(e)
