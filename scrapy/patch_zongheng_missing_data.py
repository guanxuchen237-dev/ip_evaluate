import sys
import os
import time
import random
import pymysql
import logging
import requests
import re
import subprocess
from lxml import etree
from concurrent.futures import ThreadPoolExecutor, as_completed

# 纵横配置
ZONGHENG_DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.zongheng.com/rank'
}

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def solve_waf_cookie(html, book_id):
    m_render = re.search(r'<textarea id="renderData"[^>]*>(.*?)</textarea>', html, flags=re.S)
    m_script = re.search(r'<script[^>]*name="aliyunwaf[^>]*">(.*?)</script>', html, flags=re.S)
    
    if not m_render or not m_script:
        return None
        
    renderData = m_render.group(1).strip()
    script_content = m_script.group(1).strip()
    
    js_code = f"""
        var window = {{}};
        var document = {{cookie: '', referrer: ''}};
        var location = {{href: ''}};
        var navigator = {{userAgent: 'Mozilla/5.0'}};
        var renderData = {renderData};
        var arg1 = renderData.l1.slice(10, 60);
        function setCookie(e, r) {{ 
            if (e === 'acw_sc__v2') {{
                console.log(r);
                process.exit(0);
            }}
        }}
        function reload(e) {{
            console.log(e); 
            process.exit(0);
        }}
        {script_content}
    """
    
    filename = f'solve_{book_id}.js'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(js_code)
        
    try:
        out = subprocess.check_output(['node', filename], timeout=5).decode('utf-8').strip()
        os.remove(filename)
        return out
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        logging.error(f"Node 执行失败: {e}")
        return None


def fetch_zongheng_detail(book_id, title):
    """三维解析引擎：保证更新时间与简介同时获取"""
    chapter_url = f"https://book.zongheng.com/showchapter/{book_id}.html"
    pc_detail_url = f"https://book.zongheng.com/book/{book_id}.html"
    
    session = requests.Session()
    session.trust_env = False
    data = {'updated_at': '', 'latest_chapter': '', 'abstract': ''}
    
    def parse_from_chapter_page(content):
        tree = etree.HTML(content)
        # 目录页顶级元数据提取 (新版结构)
        spans = tree.xpath('//div[@class="book-meta"]//p/span')
        for span in spans:
            txt = "".join(span.xpath('.//text()')).strip()
            if '更新时间' in txt:
                data['updated_at'] = txt.replace('更新时间：', '').replace('更新时间:', '').strip()
            elif '最新章节' in txt:
                data['latest_chapter'] = txt.replace('最新章节：', '').replace('最新章节:', '').strip()
        
        # 兜底旧版结构 (book-new-chapter)
        if not data['updated_at']:
            lc = tree.xpath('//div[@class="book-new-chapter"]//div[@class="tit"]//a/text()')
            ut = tree.xpath('//div[@class="book-new-chapter"]//div[@class="tit"]//span/text()')
            if lc: data['latest_chapter'] = lc[0].strip()
            if ut: data['updated_at'] = re.sub(r'[^\d\- :]', '', ut[0].strip()).strip()

    try:
        # 1. 优先尝试目录页 (主要查更新时间和最新章节，防风控最强)
        try:
            resp = session.get(chapter_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and 'chapterlist' in resp.text:
                parse_from_chapter_page(resp.text)
        except Exception as e:
            pass
            
        # 2. 获取 PC 详情页 (查简介)
        # 如果简介没拿到，或者简介是纵横的默认SEO文本，使用 PC 详情页
        try:
            resp_pc = session.get(pc_detail_url, headers=HEADERS, timeout=10)
            html_text = resp_pc.text
            
            if resp_pc.status_code == 200:
                if 'aliyun_waf' in html_text or '<textarea id="renderData"' in html_text:
                    cookie_val = solve_waf_cookie(html_text, book_id)
                    if cookie_val:
                        headers_with_cookie = HEADERS.copy()
                        headers_with_cookie['Cookie'] = f"acw_sc__v2={cookie_val}"
                        resp_pc = session.get(pc_detail_url, headers=headers_with_cookie, timeout=10)
                        html_text = resp_pc.text
                
                content = html_text
                import html
                
                # 提取 NUXT 数据中的真实简介
                m = re.search(r'description:"(.*?)"', content)
                if m:
                    abs_val = m.group(1).replace('\\u003Cbr\\u003E', '\n').replace('\\u003C/p\\u003E', '\n').replace('\\u003Cp\\u003E', '')
                    abs_val = html.unescape(abs_val).strip()
                    if abs_val and '纵横中文网' not in abs_val:
                        data['abstract'] = abs_val
                        
                # 兜底：如果更新时间或最新章节为空，也可以从 NUXT 数据提取
                if not data['latest_chapter']:
                    m_chap = re.search(r'latestChapterName:"(.*?)"', content)
                    if m_chap: data['latest_chapter'] = m_chap.group(1).strip()
                if not data['updated_at']:
                    m_time = re.search(r'latestDateMsg:"(.*?)"', content)
                    if m_time: data['updated_at'] = m_time.group(1).strip()
        except Exception as e:
            logging.error(f"  ❌ PC详情抓取失败: {e}")
            pass

        # 最终清洗默认的无用简介
        if data['abstract'] and '纵横中文网' in data['abstract'] and '最新力作' in data['abstract']:
            data['abstract'] = ''

        if data['updated_at'] or data['abstract']:
            return data
            
        return None
    except Exception as e:
        logging.error(f"  ❌ 抓取总控 {title}({book_id}) 出错: {e}")
        return None

def patch_zongheng_missing_data():
    print("\n" + "="*60)
    print("🚀 纵横数据库极速补全工具 (WAF Bypass 版) v2.0")
    print("特性：Node.js破解WAF | 单线程慢速模式 | 全量回填")
    print("="*60 + "\n")
    
    try:
        conn = pymysql.connect(**ZONGHENG_DB_CONFIG)
        cursor = conn.cursor()
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return

    # 1. 查找所有需要补全的唯一 book_id (包含时间或简介为空)
    query = """
        SELECT DISTINCT book_id, title
        FROM zongheng_book_ranks 
        WHERE (updated_at IS NULL OR TRIM(updated_at) = '') 
           OR (abstract IS NULL OR TRIM(abstract) = '')
        LIMIT 10000
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("✅ 检查完毕：纵横表中没有记录缺失时间，无需补全。")
        conn.close()
        return
        
    print(f"📋 检测到 {len(rows)} 本书籍需要补全。")
    print("🚀 启动单线程模式以防风控...\n")
    
    success_count = 0
    fail_count = 0
    total_books = len(rows)

    for book_id, title in rows:
        # 随机休眠防封
        time.sleep(random.uniform(1.0, 3.0))
        data = fetch_zongheng_detail(book_id, title)
            
        if data and (data.get('updated_at') or data.get('abstract')):
            try:
                update_sql = """
                    UPDATE zongheng_book_ranks 
                    SET 
                        updated_at = COALESCE(NULLIF(%s, ''), updated_at),
                        latest_chapter = COALESCE(NULLIF(%s, ''), latest_chapter),
                        abstract = COALESCE(NULLIF(%s, ''), abstract)
                    WHERE book_id = %s 
                        AND ((updated_at IS NULL OR TRIM(updated_at) = '') OR (abstract IS NULL OR TRIM(abstract) = ''))
                """
                update_cursor = conn.cursor()
                update_cursor.execute(update_sql, (
                    data['updated_at'], 
                    data['latest_chapter'], 
                    data['abstract'], 
                    book_id
                ))
                conn.commit()
                success_count += 1
                affected = update_cursor.rowcount
                abst_len = len(data['abstract']) if data['abstract'] else 0
                print(f"  ✅ [完成] {title} ({book_id}) | 时间: {data['updated_at']} | 简介: {abst_len}字 | 影响: {affected}")
            except Exception as e:
                logging.error(f"  ❌ 更新 {title} 入库失败: {e}")
                fail_count += 1
        else:
            fail_count += 1
            print(f"  ⚠️ [跳过] {title} ({book_id}) 未能获取有效数据.")

    print("\n" + "="*60)
    print(f"🏁 任务总结报告 (纵横慢速版):")
    print(f"   - 总书籍数: {total_books}")
    print(f"   - 成功同步: {success_count}")
    print(f"   - 失败/跳过: {fail_count}")
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    patch_zongheng_missing_data()
