import pymysql

def merge_qidian_data():
    conn = pymysql.connect(host='localhost', user='root', password='root', autocommit=True)
    cursor = conn.cursor()

    print("Optimizing Qidian backup table...")
    try:
        cursor.execute("ALTER TABLE qidian_backup.novel_monthly_stats ADD INDEX idx_nym (novel_id, year, month);")
    except Exception as e:
        print("Index might exist or error:", e)

    print("Restoring original data from qidian_backup to qidian_data...")
    sql = """
    UPDATE qidian_data.novel_monthly_stats current
    JOIN qidian_backup.novel_monthly_stats backup 
    ON current.novel_id = backup.novel_id AND current.year = backup.year AND current.month = backup.month
    SET current.monthly_tickets_on_list = backup.monthly_tickets_on_list,
        current.monthly_ticket_count = backup.monthly_ticket_count,
        current.rank_on_list = backup.rank_on_list,
        current.word_count = backup.word_count,
        current.collection_count = backup.collection_count;
    """
    try:
        cursor.execute(sql)
        print("Successfully merged Qidian backup data into main database.")
    except Exception as e:
        print("Error merging Qidian:", e)

    conn.close()

if __name__ == '__main__':
    merge_qidian_data()
