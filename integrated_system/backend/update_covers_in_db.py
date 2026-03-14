import pymysql

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def update_qidian_covers():
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        cursor = conn.cursor()
        
        print("Fetching Qidian records needing cover updates...")
        cursor.execute("SELECT id, novel_id FROM novel_monthly_stats WHERE novel_id IS NOT NULL AND (cover_url IS NULL OR cover_url = '')")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} records to update.")
        
        count = 0
        for rid, novel_id in rows:
            cover_url = f"https://bookcover.yuewen.com/qdbimg/349573/{novel_id}/150.webp"
            cursor.execute("UPDATE novel_monthly_stats SET cover_url=%s WHERE id=%s", (cover_url, rid))
            count += 1
            if count % 100 == 0:
                print(f"Updated {count} records...")
                
        conn.commit()
        conn.close()
        print(f"🎉 Successfully updated {count} records with cover_url in qidian_data.novel_monthly_stats")
        
    except Exception as e:
        print(f"❌ Error updating covers: {e}")

if __name__ == '__main__':
    update_qidian_covers()
