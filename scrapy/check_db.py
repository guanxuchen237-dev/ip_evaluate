import pymysql

try:
    print("--- Qidian Data ---")
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='root', database='qidian_data')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT year, month FROM novel_monthly_stats ORDER BY year DESC, month DESC")
    for row in cursor.fetchall():
        print(f"Year: {row[0]}, Month: {row[1]}")
    conn.close()
except Exception as e:
    print(e)
    
try:
    print("--- Zongheng Data ---")
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='root', database='zongheng_analysis_v8')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT year, month FROM zongheng_book_ranks ORDER BY year DESC, month DESC")
    for row in cursor.fetchall():
        print(f"Year: {row[0]}, Month: {row[1]}")
    conn.close()
except Exception as e:
    print(e)
