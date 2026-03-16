import sys
sys.path.append('scrapy')
import pymysql
import requests
from qidian_sync_intro import QIDIAN_CONFIG

def check_missing_books():
    conn = pymysql.connect(**QIDIAN_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT DISTINCT title, novel_id FROM novel_monthly_stats WHERE cover_url IS NULL OR cover_url = '' LIMIT 10")
    books = cursor.fetchall()
    conn.close()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
    }
    
    print("--- 空缺书籍存活状态检查 ---")
    for b in books:
        novel_id = b['novel_id']
        url = f"https://m.qidian.com/book/{novel_id}.html"
        try:
            # 禁用本地可能失效的代理代理
            session = requests.Session()
            session.trust_env = False
            r = session.get(url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                if '作品不存在' in r.text or '页面找不到了' in r.text or 'error-page' in r.text:
                    print(f"[!] 下架/屏蔽: {b['title']} ({novel_id})")
                else:
                    print(f"[√] 正常访问: {b['title']} ({novel_id}) - 但未抓取到数据")
            else:
                print(f"[x] 请求失败: {b['title']} (HTTP: {r.status_code})")
        except Exception as e:
            print(f"[-] 访问异常: {b['title']} ({e})")

if __name__ == '__main__':
    check_missing_books()
