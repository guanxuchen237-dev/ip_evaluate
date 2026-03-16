import pymysql
import sys

def check():
    conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', charset='utf8mb4')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
    SELECT word_count, sub_category, author, category
    FROM novel_monthly_stats
    WHERE title = '诡秘之主'
    ORDER BY monthly_tickets_on_list DESC
    LIMIT 1
    """)
    print("Top record info for Guimi:", cursor.fetchone())
    
    conn.close()

if __name__ == '__main__':
    check()
