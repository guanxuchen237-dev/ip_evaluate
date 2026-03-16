"""
纵横小说全站数据爬虫 V9.0 (代理池+翻页+并发版)
- 新增：IP代理池 (自动读取/刷新/移除 ip_addr.txt)
- 新增：自定义并发数
- 新增：翻页功能 (Page 1 -> N)
- 新增：日期范围自定义
"""
import requests
import re
import time
import logging
import json
import pymysql
import os
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ============== 1. 配置区域 ==============
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.zongheng.com/rank',
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
print_lock = Lock()

# ============== 2. 代理池管理器 (ProxyManager) ==============
class ProxyManager:
    """代理管理器：实现自动加载、验证和失效删除"""
    def __init__(self, proxy_file="ip_addr.txt"):
        self.proxy_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), proxy_file)
        self.api_url = "http://api.tianqiip.com/getip?secret=2rl0bxsd5sftel1k&num=10&type=txt&port=1&time=10&mr=1&sign=cc1cf97695ca37a8da0a5779fef4b954"
        self.proxies = []
        self.last_load_time = 0
        self.lock = Lock()
        self.load_proxies()

    def load_proxies(self):
        """从文件加载代理"""
        with self.lock:
            if not os.path.exists(self.proxy_file):
                # 尝试创建空文件
                with open(self.proxy_file, 'w', encoding='utf-8') as f: pass
                self.proxies = []
                return

            try:
                # 总是重新读取文件，确保同步
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                
                valid_proxies = []
                for p in lines:
                    if ":" in p:
                        if not p.startswith("http"):
                            valid_proxies.append(f"http://{p}")
                        else:
                            valid_proxies.append(p)
                
                self.proxies = valid_proxies
            except Exception as e:
                print(f"代理加载失败: {e}")

    def fetch_proxies_from_api(self):
        """从API获取新代理并写入文件"""
        print("🌐 正在从API获取新代理...")
        try:
            # 不使用代理去请求API
            session = requests.Session()
            session.trust_env = False
            resp = session.get(self.api_url, timeout=10, verify=False)
            if resp.status_code == 200:
                text = resp.text.strip()
                if "{" in text: # 可能返回的是json错误信息
                    print(f"❌ API返回可能包含错误: {text}")
                    return
                
                new_proxies = []
                lines = text.split('\r\n')
                for line in lines:
                    line = line.strip()
                    if ":" in line and not line.startswith("{"):
                         new_proxies.append(line) # API通常返回 ip:port 格式
                
                if new_proxies:
                    with self.lock:
                        # 追加到文件
                        with open(self.proxy_file, 'a', encoding='utf-8') as f:
                            f.write("\n")
                            for p in new_proxies:
                                f.write(f"{p}\n")
                        print(f"✅ 成功获取并写入 {len(new_proxies)} 个新代理")
                    self.load_proxies() # 重新加载
                else:
                    print("⚠️ API返回内容为空或格式无法解析")
            else:
                 print(f"❌ API请求失败: {resp.status_code}")
        except Exception as e:
            print(f"❌ 获取代理异常: {e}")

    def get_valid_proxy(self):
        """获取一个可用代理 (自动补充)"""
        # 1. 如果内存里没代理，先加载
        if not self.proxies:
            self.load_proxies()
        
        # 2. 如果加载后还是没有，或者所有都被标记为bad(虽然现在是直接删)，尝试API获取
        if not self.proxies:
            self.fetch_proxies_from_api()
        
        with self.lock:
            if self.proxies:
                return random.choice(self.proxies)
        return None

    def mark_bad(self, proxy):
        """标记代理失效，并直接从文件删除"""
        if not proxy: return
        
        # 标准化代理字符串用于匹配 (去掉 http://)
        raw_proxy = proxy.replace("http://", "").replace("https://", "")
        
        with self.lock:
            # 1. 内存移除
            if proxy in self.proxies:
                self.proxies.remove(proxy)
            
            # 2. 文件移除
            try:
                if os.path.exists(self.proxy_file):
                    with open(self.proxy_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    urls_to_remove = [raw_proxy, proxy] # 尝试匹配不带http和带http的
                    
                    removed = False
                    for line in lines:
                        clean_line = line.strip()
                        # 如果这一行包含我们要删除的ip:port
                        if any(u in clean_line for u in urls_to_remove) and clean_line:
                            removed = True
                            continue # 跳过写入，即删除
                        new_lines.append(line)
                    
                    if removed:
                        with open(self.proxy_file, 'w', encoding='utf-8') as f:
                            f.writelines(new_lines)
                        print(f"🗑️ 已永久移除失效代理: {proxy}")
            except Exception as e:
                print(f"❌ 移除代理文件失败: {e}")

    def mark_good(self, proxy):
        pass # 既然坏的直接删了，那好的就不需要额外处理了

    def remove_proxy(self, invalid_proxy):
        self.mark_bad(invalid_proxy)

proxy_manager = ProxyManager()

# ============== 3. 网络请求工具 (封装代理重试) ==============

def safe_request(method, url, params=None, data=None, headers=None, timeout=5, max_retries=3):
    """
    通用请求封装：失败自动重试，超时时间减短，智能屏蔽坏代理
    """
    if headers is None: headers = HEADERS
    
    for i in range(max_retries):
        proxy_url = proxy_manager.get_valid_proxy()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        
        try:
            # 只有第一次尝试或者成功后才sleep，失败重试时不sleep或者sleep短一点
            if i > 0: time.sleep(0.5) 
            
            session = requests.Session()
            session.trust_env = False
            if method.upper() == 'GET':
                resp = session.get(url, params=params, headers=headers, proxies=proxies, timeout=timeout, verify=False)
            else:
                resp = session.post(url, data=data, json=params, headers=headers, proxies=proxies, timeout=timeout, verify=False)
            
            if resp.status_code == 200:
                proxy_manager.mark_good(proxy_url) # 成功，奖励
                return resp
            elif resp.status_code in [403, 429]:
                 print(f"⚠️ {resp.status_code} Forbidden - IP: {proxy_url}")
                 proxy_manager.mark_bad(proxy_url) # 视为失败
            else:
                pass 
                
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            print(f"⚠️ 连接异常 ({type(e).__name__}) - IP: {proxy_url}")
            proxy_manager.mark_bad(proxy_url) # 记过
        except Exception as e:
            logging.warning(f"⚠️ 其他请求异常: {e}")
            pass
    # --- 最终兜底：尝试直连 ---
    try:
        logging.info(f"🌐 尝试【直连兜底】访问: {url}")
        session = requests.Session()
        session.trust_env = False
        if method.upper() == 'GET':
            resp = session.get(url, params=params, headers=headers, proxies={"http": None, "https": None}, timeout=timeout, verify=False)
        else:
            resp = session.post(url, data=data, json=params, headers=headers, proxies={"http": None, "https": None}, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp
    except Exception as e:
        print(f"⚠️ 直连兜底也失败了: {e}")
            
    return None

# ============== 4. 数据库工具 ==============

def get_db_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def init_db():
    conn = pymysql.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.select_db(DB_CONFIG['database'])
    
    # 1. 书籍榜单表 
    sql_books = """
    CREATE TABLE IF NOT EXISTS zongheng_book_ranks (
        year INT,
        month INT,
        book_id VARCHAR(20),
        title VARCHAR(100),
        author VARCHAR(100),
        category VARCHAR(50),
        word_count INT COMMENT '字数',
        monthly_ticket INT COMMENT '月票数',
        rank_num INT COMMENT '排名',
        month_donate INT DEFAULT 0 COMMENT '本月捧场',
        total_click BIGINT COMMENT '总点击',
        total_rec BIGINT COMMENT '总推荐',
        week_rec INT DEFAULT 0 COMMENT '周推荐',
        post_count INT DEFAULT 0 COMMENT '圈子帖子数',
        fan_count INT DEFAULT 0 COMMENT '圈子粉丝数',
        
        -- 新增字段
        update_frequency VARCHAR(50) COMMENT '更新频率',
        chapter_interval VARCHAR(50) COMMENT '章节间隔(最近更新)',
        
        is_signed VARCHAR(20),
        status VARCHAR(20),
        updated_at VARCHAR(50) COMMENT '更新时间',
        book_url VARCHAR(255),
        cover_url VARCHAR(255) COMMENT '封面链接',
        abstract TEXT COMMENT '简介',
        latest_chapter VARCHAR(255) COMMENT '最新章节',
        forum_id VARCHAR(20),
        crawl_time DATETIME,
        PRIMARY KEY (year, month, book_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 2. 评论表
    sql_comments = """
    CREATE TABLE IF NOT EXISTS zongheng_book_comments (
        thread_id BIGINT PRIMARY KEY,
        book_id VARCHAR(20),
        book_title VARCHAR(100),
        user_id BIGINT,
        nickname VARCHAR(100),
        content TEXT,
        content_length INT,
        create_time BIGINT,
        comment_date DATETIME,
        data_source_ym VARCHAR(20),
        ip_region VARCHAR(50),
        crawl_time DATETIME,
        INDEX idx_book (book_id),
        INDEX idx_ym (data_source_ym)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    cursor.execute(sql_books)
    cursor.execute(sql_comments)
    
    # --- 自动迁移：检查并添加新字段 (防止旧表报错) ---
    try:
        cursor.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN update_frequency VARCHAR(50) COMMENT '更新频率'")
        print("🛠️ 已自动添加列: update_frequency")
    except Exception:
        pass # 列已存在

    try:
        cursor.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN chapter_interval VARCHAR(50) COMMENT '章节间隔'")
        print("🛠️ 已自动添加列: chapter_interval")
    except Exception:
        pass # 列已存在

    try:
        cursor.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN abstract TEXT COMMENT '简介'")
        print("🛠️ 已自动添加列: abstract")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN latest_chapter VARCHAR(255) COMMENT '最新章节'")
        print("🛠️ 已自动添加列: latest_chapter")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN updated_at VARCHAR(50) COMMENT '更新时间'")
        print("🛠️ 已自动添加列: updated_at")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("✅ 数据库表结构检查完成 (新增: 频率/间隔/简介/最新章节)")

# ============== 5. 核心爬虫逻辑 ==============

def parse_nuxt_value(text, key_pattern):
    """【移植自Monthly爬虫】智能解析Nuxt JSON数据，支持压缩变量"""
    try:
        # 1. 先尝试直接匹配 (如 totalWords:123)
        direct = re.search(key_pattern + r'\s*:\s*(\d+)', text)
        if direct: return int(direct.group(1))
        
        # 2. 匹配压缩变量名 (如 totalWords:f)
        var_match = re.search(key_pattern + r'\s*:\s*([a-z])\b', text)
        if not var_match: return 0
        
        var_name = var_match.group(1)
        
        # 提取 window.__NUXT__=(function(a,b...){...}(val1,val2...))
        # 通常这部分在页面底部脚本中
        nuxt_start = text.find('window.__NUXT__=')
        if nuxt_start < 0: return 0
        
        # 截取合理的长度进行搜索 (比如50KB)
        search_text = text[nuxt_start : nuxt_start + 50000]
        
        # 匹配函数参数定义: function(a,b,c,d,e,f...)
        func_params_match = re.search(r'\(function\(([^)]+)\)', search_text)
        if not func_params_match: return 0
        
        params_str = func_params_match.group(1)
        params = [p.strip() for p in params_str.split(',')]
        
        # 找到变量名在参数列表中的索引
        try:
            var_index = params.index(var_name)
        except ValueError: return 0
        
        # 匹配IIFE的参数调用部分: }(val1, val2, ...));
        # 这是一个从后往前的查找过程
        # 先找到脚本结束标签
        end_script = search_text.rfind('</script>')
        if end_script < 0: end_script = len(search_text)
        
        # 找到最后一个 }(
        last_call_start = search_text.rfind('}(', 0, end_script)
        if last_call_start < 0: return 0
        
        # 找到结束的 ));
        last_call_end = search_text.find('));', last_call_start)
        if last_call_end < 0: return 0
        
        # 提取参数值字符串
        # 注意: 参数值里可能有字符串、数字、null等，用逗号分隔
        # 简单的 split(',') 可能被字符串里的逗号坑，但Nuxt传参通常较规范
        args_str = search_text[last_call_start+2 : last_call_end]
        
        # 简易解析：分割并处理引号
        # 生产环境可能需要更复杂的解析器，但对于数字类型通常够用
        args = []
        # 使用正则 split，忽略引号内的逗号 (简化版，假设数字不含逗号)
        raw_args = args_str.split(',') 
        # 为了更准确，最好完全模拟JS参数解析，但这里做个近似
        # 如果参数数量和变量数量对不上，尽量对齐
        
        if var_index < len(raw_args):
            val = raw_args[var_index].strip()
            # 去除引号
            val = val.replace('"', '').replace("'", "")
            if val.isdigit():
                return int(val)
                
        return 0
    except Exception:
        return 0

def extract_stat(text, pattern, factor=1):
    m = re.search(pattern, text)
    if m:
        try: return int(float(m.group(1)) * factor)
        except: return 0
    return 0

def fetch_forum_data_regex(forum_id):
    """【修复】圈子数据: 优先解析 <div class="forums-nums">"""
    if not forum_id or forum_id == '0': return 0, 0
    try:
        url = f'https://forum.zongheng.com/{forum_id}.html'
        resp = safe_request('GET', url, timeout=5)
        if not resp: return 0, 0
        text = resp.text
        
        p_num = 0
        f_num = 0
        
        # Method 1: <div class="forums-nums"> (Most robust for Zongheng)
        nums_div = re.search(r'<div[^>]*class="forums-nums"[^>]*>(.*?)</div>', text, re.DOTALL)
        if nums_div:
            div_content = nums_div.group(1)
            # <span><i>帖子数</i>123</span>
            spans = re.findall(r'<span[^>]*>(.*?)</span>', div_content, re.DOTALL)
            if len(spans) >= 2:
                try:
                    p_text = re.sub(r'<[^>]+>', '', spans[0]).strip()
                    f_text = re.sub(r'<[^>]+>', '', spans[1]).strip()
                    
                    p_digits = re.search(r'(\d+)', p_text)
                    if p_digits: p_num = int(p_digits.group(1))
                    
                    f_digits = re.search(r'(\d+)', f_text)
                    if f_digits: f_num = int(f_digits.group(1))
                    
                    return p_num, f_num
                except: pass

        # Method 2: Fallback regex
        p_m = re.search(r'帖子数\s*</i>\s*(\d+)', text) or re.search(r'>\s*(\d+)\s*<[^>]*>\s*帖子', text)
        if p_m: p_num = int(p_m.group(1))
            
        f_m = re.search(r'粉丝数\s*</i>\s*(\d+)', text) or re.search(r'>\s*(\d+)\s*<[^>]*>\s*粉丝', text)
        if f_m: f_num = int(f_m.group(1))
            
        return p_num, f_num
    except: return 0, 0

def parse_book_detail_ultimate(api_book):
    """【终极解析】补全 Author, WeekRec, PostCount, UpdateFreq"""
    book_id = str(api_book.get('bookId'))
    url = f"https://book.zongheng.com/book/{book_id}.html"
    
    book = {
        'book_id': book_id,
        'title': api_book.get('bookName', ''),
        'author': api_book.get('authorName') or api_book.get('pseudonym') or '',
        'monthly_ticket': int(api_book.get('number', 0)),
        'category': api_book.get('cateFineName', ''),
        'status': '连载中' if api_book.get('serialStatus') == 0 else '已完结',
        'book_url': url,
        'cover_url': '',
        'abstract': '',
        'latest_chapter': '',
        'is_signed': '未签约',
        'forum_id': None,
        'word_count': 0, 'total_click': 0, 'total_rec': 0, 'week_rec': 0,
        'month_donate': 0, 'post_count': 0, 'fan_count': 0,
        'update_frequency': '未知', 'chapter_interval': '未知', 'updated_at': ''
    }

    try:
        resp = safe_request('GET', url, timeout=10)
        if not resp: 
            print(f"❌ 详情页无法访问: {book['title']}")
            return book
            
        text = resp.text
        
        # --- 修复：作者名 ---
        if not book['author']:
            m = re.search(r'property="og:novel:author" content="([^"]+)"', text)
            if m: book['author'] = m.group(1)
            else:
                m2 = re.search(r'class="au-name"[^>]*>\s*<a[^>]*>(.*?)</a>', text)
                if m2: book['author'] = m2.group(1).strip()
                else:
                    m3 = re.search(r'<title>.*?_(.*?)_.*?</title>', text)
                    if m3: book['author'] = m3.group(1).strip()

        # --- 获取封面 ---
        m_img = re.search(r'(?:property|name)="og:image"\s*content="([^"]+)"', text)
        if m_img: book['cover_url'] = m_img.group(1)

        # --- 获取简介与最新章节 ---
        m_abs = re.search(r'(?:property|name)="og:description"\s*content="([^"]+)"', text)
        if m_abs:
            abs_str = m_abs.group(1).strip()
            import html
            abs_str = html.unescape(abs_str)
            if abs_str.startswith('content="'):
                abs_str = abs_str.replace('content="', '', 1)
                if abs_str.endswith('"'):
                    abs_str = abs_str[:-1]
            if '观看小说：' in abs_str:
                abs_str = abs_str.split('观看小说：')[-1].strip()
            book['abstract'] = abs_str
        else:
            m_abs2 = re.search(r'class="book-dec[^>]*>.*?<p>(.*?)</p>', text, re.DOTALL)
            if m_abs2:
                book['abstract'] = re.sub(r'<[^>]+>', '', m_abs2.group(1)).strip()

        m_chap = re.search(r'(?:property|name)="og:novel:latest_chapter_name"\s*content="([^"]+)"', text)
        if m_chap:
            book['latest_chapter'] = m_chap.group(1).strip()
        else:
            m_chap2 = re.search(r'class="tit"\s+target="_blank"\s+title="([^"]+)"', text)
            if m_chap2:
                book['latest_chapter'] = m_chap2.group(1).strip()

        # --- 数据提取 (融合 HTML正则 + Nuxt智能解析) ---
        
        # 1. 字数
        book['word_count'] = extract_stat(text, r'totalWords:(\d+)') or \
                             extract_stat(text, r'<i>([\d.]+)\s*</i>\s*万字数', 10000)
        if book['word_count'] == 0:
            book['word_count'] = parse_nuxt_value(text, 'totalWords')
            
        # 2. 总点击
        book['total_click'] = extract_stat(text, r'totalClick:(\d+)') or \
                              extract_stat(text, r'<i>([\d.]+)\s*</i>\s*万总点击', 10000)
        if book['total_click'] == 0:
             book['total_click'] = parse_nuxt_value(text, 'totalClick')

        # 3. 总推荐
        book['total_rec'] = extract_stat(text, r'totalRecCount:(\d+)') or \
                            extract_stat(text, r'<i>([\d.]+)\s*</i>\s*万总推荐', 10000)
        if book['total_rec'] == 0:
            book['total_rec'] = parse_nuxt_value(text, 'totalRecCount')
        
        # 4. 周推荐
        book['week_rec'] = extract_stat(text, r'weekRecCount:(\d+)')
        if book['week_rec'] == 0:
            book['week_rec'] = parse_nuxt_value(text, 'weekRecCount')
            if book['week_rec'] == 0:
                book['week_rec'] = extract_stat(text, r'(\d+)\s*</span>\s*<i[^>]*>\s*周推荐')
                if book['week_rec'] == 0:
                    book['week_rec'] = extract_stat(text, r'<i>(\d+)\s*</i>\s*周推荐')

        # 5. 本月捧场
        book['month_donate'] = extract_stat(text, r'thisMonthDonateNum:(\d+)')
        if book['month_donate'] == 0:
             book['month_donate'] = parse_nuxt_value(text, 'thisMonthDonateNum')
        
        # 签约
        if 'class="vip"' in text or '"signStatus":1' in text or '已签约' in text:
            book['is_signed'] = '已签约'
            
        # --- 新增：更新频率 (优化显示逻辑) ---
        # 1. 优先显示今日日更
        today_up_match = re.search(r'["\']?todayUpdateNum["\']?\s*:\s*(\d+)', text)
        up_num = int(today_up_match.group(1)) if today_up_match else 0
        
        book['update_frequency'] = "未知"
        
        if up_num > 0:
            book['update_frequency'] = f"日更{up_num}字"
        else:
            # 2. 若今日未更，尝试显示"本月更X天"
            # 匹配: >18</b> ... >天</i> ... >本月更新
            md_match = re.search(r'>(\d+)\s*</b>\s*<[iI][^>]*>\s*天\s*</[iI]>\s*</span>\s*<[pP][^>]*>\s*本月更新', text)
            if md_match:
                days = int(md_match.group(1))
                if days > 0:
                     book['update_frequency'] = f"本月更{days}天"
                else:
                     book['update_frequency'] = "本月未更"
            else:
                 book['update_frequency'] = "暂无更新"
                
        # --- 新增：章节间隔 (优先匹配时间戳，失败则匹配日期字符串) ---
        last_up_match = re.search(r'["\']?updateTime["\']?\s*:\s*(\d{13})', text)
        dt = None
        
        if last_up_match:
            ts = int(last_up_match.group(1)) / 1000
            dt = datetime.fromtimestamp(ts)
        else:
            # 尝试匹配 "latestDateMsg": "2025-12-24 00:25:49"
            date_match = re.search(r'["\']?latestDateMsg["\']?\s*:\s*["\']([^"\']+)["\']', text)
            
            # 宽泛匹配页面上的日期 (取最近的一个，通常是更新时间)
            if not date_match:
                # 寻找形如 2025-12-24 00:25:49 的时间 (使用 . 兼容 nbsp 等特殊空白)
                dates = re.findall(r'(\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2})', text)
                if dates:
                    # 过滤掉老的创建时间等，取最大的时间
                    valid_dates = []
                    for d_str in dates:
                        try:
                            # 替换可能得特殊分隔符为空格
                            clean = d_str[:10] + ' ' + d_str[11:]
                            valid_dates.append(datetime.strptime(clean, "%Y-%m-%d %H:%M:%S"))
                        except: pass
                    if valid_dates:
                        dt = max(valid_dates)

            if date_match and not dt:
                try:
                    dt = datetime.strptime(date_match.group(1), "%Y-%m-%d %H:%M:%S")
                except: pass

        if dt:
            book['updated_at'] = dt.strftime("%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = now - dt
            days = diff.days
            if days == 0:
                seconds = diff.seconds
                hours = seconds // 3600
                if hours == 0:
                    book['chapter_interval'] = f"{seconds // 60}分钟前"
                else:
                    book['chapter_interval'] = f"{hours}小时前"
            else:
                book['chapter_interval'] = f"{days}天前"
        
        # --- 圈子数据 ---
        # 兼容 detailForumsInfoBookId:123 或 "forumId":"123"
        f_match = re.search(r'["\']?(?:detailForumsInfoBookId|forumId)["\']?\s*[:]\s*["\']?(\d+)["\']?', text)
        if f_match:
            book['forum_id'] = f_match.group(1)
            p, f = fetch_forum_data_regex(book['forum_id'])
            book['post_count'] = p
            book['fan_count'] = f

        return book
    except Exception as e:
        print(f"详情解析异常 {book['title']}: {e}")
        return book

def fetch_monthly_list(year, month, page, limit):
    """获取指定页码的月榜列表"""
    rank_no = f"{year}{month:02d}"
    url = "https://www.zongheng.com/api/rank/details"
    data = {
        "rankNo": rank_no, 
        "rankType": "1", 
        "pageNum": str(page),  # 动态页码
        "pageSize": str(limit), 
        "isNewBook": "1", 
        "cateFineId": "0", "cateType": "0"
    }
    # 使用 safe_request
    resp = safe_request('POST', url, data=data)
    if resp:
        return resp.json().get('result', {}).get('resultList', [])
    return []

def fetch_comments_simple(book_info, archive_ym):
    """抓取评论"""
    if not book_info['forum_id']: return 0
    conn = get_db_conn()
    cursor = conn.cursor()
    count = 0; mark = ""; page = 1
    
    # 最多抓取5页评论
    while page <= 5:
        try:
            params = {"bookId": book_info['book_id'], "mark": mark, "forumId": book_info['forum_id'], "forumType": "0", "_": int(time.time()*1000), "callback": "cb"}
            # 使用 safe_request (GET)
            resp = safe_request('GET', "https://forum.zongheng.com/api/forums/postlist", params=params, timeout=5)
            if not resp: break
            
            json_str = re.search(r'cb\((.*)\)', resp.text)
            if not json_str: break
            data = json.loads(json_str.group(1))
            if data.get("status") != 1: break
            threads = data["data"].get("ThreadList", [])
            if not threads: break
            
            values = []
            now = datetime.now()
            for t in threads:
                content = t.get('content', '')
                c_time = t.get('createTime', 0)
                fmt_date = datetime.fromtimestamp(c_time / 1000) if c_time else None
                values.append((t.get('threadId'), book_info['book_id'], book_info['title'], t.get('userId'), t.get('nickName'), content, len(content), c_time, fmt_date, archive_ym, t.get('ipRegion'), now))
            
            if values:
                sql = "INSERT IGNORE INTO zongheng_book_comments (thread_id, book_id, book_title, user_id, nickname, content, content_length, create_time, comment_date, data_source_ym, ip_region, crawl_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.executemany(sql, values)
                conn.commit()
                count += len(values)
            
            mark = data["data"].get("mark")
            if not mark: break
            page += 1
        except: break
    conn.close()
    return count

# ============== 6. 流程控制器 ==============

def process_one(api_book, year, month, idx):
    archive_ym = f"{year}-{month:02d}"
    
    # 1. 抓取
    book = parse_book_detail_ultimate(api_book)
    
    # 2. 入库
    conn = get_db_conn()
    cursor = conn.cursor()
    sql_book = """
    INSERT INTO zongheng_book_ranks 
    (year, month, book_id, title, author, category, word_count, monthly_ticket, rank_num, 
     month_donate, total_click, total_rec, week_rec, post_count, fan_count, 
     update_frequency, chapter_interval,
     is_signed, status, updated_at, book_url, cover_url, abstract, latest_chapter, forum_id, crawl_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    author=VALUES(author), post_count=VALUES(post_count), fan_count=VALUES(fan_count),
    week_rec=VALUES(week_rec), month_donate=VALUES(month_donate), is_signed=VALUES(is_signed), 
    update_frequency=VALUES(update_frequency), chapter_interval=VALUES(chapter_interval),
    updated_at=VALUES(updated_at),
    cover_url=VALUES(cover_url), abstract=VALUES(abstract), latest_chapter=VALUES(latest_chapter), crawl_time=VALUES(crawl_time)
    """
    try:
        cursor.execute(sql_book, (
            year, month, book['book_id'], book['title'], book['author'], book['category'],
            book['word_count'], book['monthly_ticket'], idx,
            book['month_donate'], book['total_click'], book['total_rec'], book['week_rec'],
            book['post_count'], book['fan_count'],
            book['update_frequency'], book['chapter_interval'],
            book['is_signed'], book['status'], book['updated_at'], book['book_url'], book['cover_url'],
            book['abstract'], book['latest_chapter'], book['forum_id'],
            datetime.now()
        ))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()
    
    # 3. 评论
    c_num = fetch_comments_simple(book, archive_ym)
    
    # console output formatting
    freq_short = book['update_frequency']
    if "日更" in freq_short:
        freq_short = freq_short.replace("日更", "日").replace("字", "")
    elif "本月更" in freq_short:
        freq_short = freq_short.replace("本月更", "月") # e.g. "月18天"
    
    intv_short = book['chapter_interval'].replace("天前", "d").replace("小时前", "h")
    
    return f"[{idx}] {book['title']:<8} | {book['author']:<4} | 票:{book['monthly_ticket']} | 频:{freq_short} | 隔:{intv_short}"

def main():
    import urllib3
    import sys
    urllib3.disable_warnings() # 屏蔽证书警告

    init_db()
    print("="*60)
    print("纵横爬虫 V9.0 - 代理池+翻页并发版")
    print("="*60)
    
    try:
        if sys.stdin and sys.stdin.isatty():
            s_date = input("起始年月 (YYYY-MM): ").strip()
            e_date = input("结束年月 (YYYY-MM): ").strip()
            limit_per_page = int(input("每页数量 (默认20): ").strip() or "20")
            page_count = int(input("抓取页数 (翻几页，默认1): ").strip() or "1")
            workers = int(input("并发线程数 (默认3): ").strip() or "3")
        else:
            s_date = datetime.now().strftime("%Y-%m")
            e_date = s_date
            limit_per_page = 20
            page_count = 1
            workers = 3
        
        start = datetime.strptime(s_date, "%Y-%m")
        end = datetime.strptime(e_date, "%Y-%m")
    except Exception as e:
        print(f"❌ 输入格式错误: {e}")
        return

    curr = start
    while curr <= end:
        y, m = curr.year, curr.month
        print(f"\n>>>>>> 正在处理 {y}-{m:02d} ...")
        
        # 循环翻页
        rank_counter = 1
        all_books = []
        
        for p in range(1, page_count + 1):
            print(f"   Getting list page {p} ...")
            page_books = fetch_monthly_list(y, m, p, limit_per_page)
            if not page_books:
                print(f"   ⚠️ 第 {p} 页无数据，停止翻页")
                break
            
            # 记录这本书的全局排名
            for b_info in page_books:
                all_books.append((b_info, rank_counter))
                rank_counter += 1
                
        print(f"   共获取 {len(all_books)} 本书籍，准备并发处理...")

        with ThreadPoolExecutor(max_workers=workers) as ex:
            # item[0]=book_info, item[1]=global_rank
            futures = [ex.submit(process_one, item[0], y, m, item[1]) for item in all_books]
            
            done_count = 0
            for f in as_completed(futures):
                done_count += 1
                try:
                    res_str = f.result()
                    with print_lock:
                        print(f"({done_count}/{len(all_books)}) {res_str}")
                except Exception as e:
                    print(f"❌ Worker Error: {e}")
        
        # 月份递增
        if m == 12: curr = datetime(y+1, 1, 1)
        else: curr = datetime(y, m+1, 1)

    print("\n✅ 所有任务已完成！")

if __name__ == '__main__':
    main()