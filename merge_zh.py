import pymysql

def merge_zh_data():
    conn = pymysql.connect(host='localhost', user='root', password='root', autocommit=True)
    cursor = conn.cursor()

    print("Optimizing Zongheng backup table...")
    try:
        cursor.execute("ALTER TABLE zh_backup.zongheng_book_ranks ADD INDEX idx_bym (book_id, year, month);")
    except Exception as e:
        print("Index might exist or error:", e)

    print("Restoring original data from zh_backup to zongheng_analysis_v8...")
    sql = """
    UPDATE zongheng_analysis_v8.zongheng_book_ranks current
    JOIN zh_backup.zongheng_book_ranks backup 
    ON current.book_id = backup.book_id AND current.year = backup.year AND current.month = backup.month
    SET current.monthly_ticket = backup.monthly_ticket,
        current.total_rec = backup.total_rec,
        current.total_click = backup.total_click,
        current.word_count = backup.word_count,
        current.post_count = backup.post_count,
        current.fan_count = backup.fan_count;
    """
    try:
        cursor.execute(sql)
        print("Successfully merged Zongheng backup data into main database.")
    except Exception as e:
        print("Error merging Zongheng:", e)

    conn.close()

if __name__ == '__main__':
    merge_zh_data()
