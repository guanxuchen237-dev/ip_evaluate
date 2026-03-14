import requests
import pymysql

def check_everything():
    print("--- 1. MySQL Direct Check ---")
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='qidian_data', charset='utf8mb4')
    with conn.cursor() as cur:
        cur.execute("SELECT id, title FROM zongheng_chapters WHERE id=121")
        row = cur.fetchone()
        title = row[1]
        print(f"Row 121: id={row[0]}")
        print(f"Raw Title: {repr(title)}")
        print(f"Length: {len(title)}")
        import binascii
        print(f"HEX: {binascii.hexlify(title.encode('utf-8')).decode().upper()}")
        print(f"Expected HEX '剑来': {binascii.hexlify('剑来'.encode('utf-8')).decode().upper()}")
    conn.close()

    print("\n--- 2. API Check ---")
    title = "剑来"
    url = f"http://localhost:5000/api/library/chapter?title={title}&chapter_num=1"
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        print(f"Response JSON: {res.json()}")
    except Exception as e:
        print(f"API failed: {e}")

if __name__ == "__main__":
    check_everything()
