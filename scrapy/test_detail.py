import qidian_sync_all
import pymysql
import requests

def test_sync():
    conn = qidian_sync_all.get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT DISTINCT novel_id, title FROM novel_monthly_stats WHERE abstract IS NULL LIMIT 2')
    books = cursor.fetchall()
    conn.close()
    
    session = requests.Session()
    session.headers = {'User-Agent': qidian_sync_all.CONST_USER_AGENT, 'Referer': 'https://www.qidian.com/'}
    session.trust_env = False
    session.proxies = {'http': None, 'https': None}
    
    for book in books:
        novel_id, title = book['novel_id'], book['title']
        print(f'Fetching: {title} (ID: {novel_id})')
        intro, latest = qidian_sync_all.fetch_book_detail(session, novel_id)
        print('Result intro:', repr(intro)[:50])
        print('Result latest:', latest)
        if intro:
            affected = qidian_sync_all.update_db(novel_id, intro, latest)
            print(f'  [v] {title} updated, DB affected: {affected}')

if __name__ == '__main__':
    test_sync()
