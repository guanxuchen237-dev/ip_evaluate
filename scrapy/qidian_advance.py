"""
起点高级爬虫 (最终修复版)
集成功能：
1. 榜单抓取 (强制表格模式 + 双重解析兜底)
2. 字体解密 (自动识别字体文件)
3. IP版权/改编信息提取 (调用 Node.js 签名)
4. Cookie 自动巡航 (优先使用本地 ChromeDriver)
5. 收藏数/收藏榜排名从收藏榜获取
6. 月票榜排名从荣誉标签提取
"""

import requests
from lxml import etree
import time
import logging
import re
import sys
import os
import io
import json
import random
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# === 依赖库检查与导入 ===
try:
    from fontTools.ttLib import TTFont
    FONT_TOOLS_AVAILABLE = True
except ImportError:
    FONT_TOOLS_AVAILABLE = False
    print("⚠️ 未安装 fonttools，月票数可能无法解密")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ 未安装 selenium，无法自动更新Cookie")

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("⚠️ 未安装 beautifulsoup4，将仅使用lxml解析")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ 未安装 playwright，无法使用浏览器内核抓取")

# 构建原生数据库连接器替代缺失的 db_connector.py
import pymysql

class DBConnector:
    def __init__(self, db_name='qidian_data'):
        self.config = {
            'host': 'localhost', 'port': 3306, 'user': 'root', 
            'password': 'root', 'database': db_name, 'charset': 'utf8mb4'
        }
        
    def save_novel_monthly(self, data):
        conn = pymysql.connect(**self.config)
        cursor = conn.cursor()
        
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        updates = ", ".join([f"{k}=VALUES({k})" for k in data.keys() if k != 'novel_id'])
        
        sql = f"INSERT INTO novel_monthly_stats ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"
        
        try:
            cursor.execute(sql, tuple(data.values()))
            conn.commit()
        except Exception as e:
            print(f"DB Insert Error: {e}")
        finally:
            conn.close()

DB_AVAILABLE = True

# 尝试导入代理池 (如果有)
try:
    from proxy_pool import get_proxy_pool
except ImportError:
    pass

class ProxyManager:
    def __init__(self, proxy_file="ip_addr.txt"):
        self.proxy_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), proxy_file)
        self.proxies = []
        self.last_reload_time = 0
        self.file_lock = Lock()
        self.reload()

    def reload(self):
        """Load proxies from file, respecting comments"""
        try:
            # Check if file modified since last reload
            if os.path.exists(self.proxy_file):
                mtime = os.path.getmtime(self.proxy_file)
                if mtime <= self.last_reload_time and self.proxies:
                    return

                with self.file_lock:
                    self.proxies = []
                    with open(self.proxy_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            raw_line = line.strip()
                            if raw_line and not raw_line.startswith('#'):
                                # Normalize proxy string
                                if not raw_line.startswith('http'):
                                    proxy = f"http://{raw_line}"
                                else:
                                    proxy = raw_line
                                if proxy not in self.proxies:
                                    self.proxies.append(proxy)
                    
                    self.last_reload_time = time.time()
                    logging.info(f"Loaded {len(self.proxies)} proxies from file")
        except Exception as e:
            logging.error(f"Failed to load proxies: {e}")

    def remove_proxy(self, invalid_proxy):
        """Remove invalid proxy from memory and file"""
        with self.file_lock:
            # 1. Remove from memory
            if invalid_proxy in self.proxies:
                self.proxies.remove(invalid_proxy)
            
            # 2. Remove from file
            try:
                if os.path.exists(self.proxy_file):
                    lines = []
                    with open(self.proxy_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    with open(self.proxy_file, 'w', encoding='utf-8') as f:
                        for line in lines:
                            # Normalize line for comparison
                            stripped = line.strip()
                            if not stripped or stripped.startswith('#'):
                                f.write(line)
                                continue
                                
                            current_proxy = stripped
                            if not current_proxy.startswith('http'):
                                current_proxy = f"http://{current_proxy}"
                            
                            if current_proxy != invalid_proxy:
                                f.write(line)
                    
                    logging.info(f"🗑️ Removed expired proxy from file: {invalid_proxy}")
            except Exception as e:
                logging.error(f"Failed to update proxy file: {e}")

    def validate_proxy(self, proxy):
        """Check if proxy is valid by requesting Qidian"""
        proxies = {"http": proxy, "https": proxy}
        try:
            start = time.time()
            # 5s timeout
            resp = requests.get("https://www.qidian.com/", proxies=proxies, timeout=5, headers={"User-Agent": CONST_USER_AGENT})
            if resp.status_code == 200:
                elapsed = (time.time() - start) * 1000
                return True, elapsed
        except:
            pass
        return False, 0

    def get_valid_proxy(self):
        """Get a validated random proxy. Reloads if needed."""
        self.reload() # Check for new proxies
        
        candidates = list(self.proxies)
        random.shuffle(candidates)
        
        for proxy in candidates:
            valid, elapsed = self.validate_proxy(proxy)
            if valid:
                logging.info(f"✅ Valid proxy: {proxy} ({elapsed:.0f}ms)")
                return proxy
            else:
                logging.warning(f"❌ Invalid/Expired proxy: {proxy}")
                self.remove_proxy(proxy)
        
        return None

    def get_all_proxies(self):
        self.reload()
        return self.proxies

proxy_manager = ProxyManager()

def get_user_proxy():
    """获取一个验证过的代理"""
    return proxy_manager.get_valid_proxy()

# === 全局配置 ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print_lock = Lock()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, 'qidian_cookies_dict.json')
LOCAL_DRIVER_PATH = r"D:\spider_code\chromedriver.exe"
CONST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# ==============================================================================
# 模块一：Cookie 管理与自动刷新
# ==============================================================================
class CookieManager:
    @staticmethod
    def renew_cookie_with_selenium(target_proxy=None):
        """使用Selenium自动获取最新Cookie (支持代理轮询重试)"""
        if not SELENIUM_AVAILABLE:
            logging.error("Selenium未安装，无法自动刷新Cookie")
            return False
            
        proxies_to_try = []
        if target_proxy:
            proxies_to_try.append(target_proxy)
        else:
            # 如果没有指定，则尝试所有代理 (随机打乱顺序)
            proxies_to_try = list(proxy_manager.get_all_proxies())
            random.shuffle(proxies_to_try)
            # 也可以尝试直连作为最后手段 (或者最前，看策略，这里放最后)
            proxies_to_try.append(None)

        for proxy in proxies_to_try:
            driver = None
            try:
                proxy_msg = f"代理[{proxy}]" if proxy else "直连"
                logging.info(f"🔄 尝试使用 {proxy_msg} 刷新Cookie...")
                
                options = Options()
                options.add_argument("--headless=new") 
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage") # 加上此项防止内存不足导致 Chrome 崩溃断开连接
                options.add_argument("--window-size=1920,1080") # 规避反爬
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument(f"user-agent={CONST_USER_AGENT}")
                options.add_argument("--ignore-certificate-errors") # 忽略SSL错误
                
                if proxy:
                    options.add_argument(f'--proxy-server={proxy}')
                
                if os.path.exists(LOCAL_DRIVER_PATH):
                    service = Service(executable_path=LOCAL_DRIVER_PATH)
                else:
                    os.environ['WDM_SSL_VERIFY'] = '0'
                    service = Service(ChromeDriverManager().install())
                
                driver = webdriver.Chrome(service=service, options=options)
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                })
                
                # 设置更长的超时
                driver.set_page_load_timeout(30)
                driver.set_script_timeout(30)

                # 1. 访问主页
                try:
                    driver.get("https://www.qidian.com/")
                except Exception as e:
                    logging.warning(f"⚠️ {proxy_msg} 访问主页超时: {e}")
                    if proxy: proxy_manager.remove_proxy(proxy)
                    continue # 换下一个代理

                time.sleep(2)
                
                # 2. 访问月票榜
                driver.get("https://www.qidian.com/rank/yuepiao/")
                
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "rank-view-list"))
                    )
                except Exception as wait_err:
                    # 如果超时，看截图或Title判断是否被封
                    title = "未知"
                    try:
                        title = driver.title
                    except Exception:
                        pass
                    logging.warning(f"⚠️ {proxy_msg} 等待元素超时或者浏览器崩溃: {wait_err}, 页面标题: {title}")
                    if proxy: proxy_manager.remove_proxy(proxy)
                    # 不立即退出，检查是否有Cookie

                time.sleep(3)
                
                selenium_cookies = driver.get_cookies()
                if not selenium_cookies:
                    if proxy: proxy_manager.remove_proxy(proxy)
                    logging.warning(f"❌ {proxy_msg} 未获取到Cookie，尝试下一个...")
                    continue
                    
                cookie_dict = {c['name']: c['value'] for c in selenium_cookies}
                cookie_dict['listStyle'] = '2'
                
                # 验证Cookie有效性 (简单检查是否有名为 _csrfToken 或 qd_rs 的cookie)
                # if '_csrfToken' not in cookie_dict:
                #     logging.warning(f"❌ {proxy_msg} 获取的Cookie可能无效 (缺关键字段)，尝试下一个...")
                #     continue

                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cookie_dict, f, ensure_ascii=False, indent=2)
                
                logging.info(f"✅ 成功! {proxy_msg} Cookie已保存至 {COOKIE_FILE}")
                return cookie_dict
                
            except Exception as e:
                logging.error(f"❌ {proxy_msg} 发生异常: {e}")
            finally:
                if driver:
                    try: driver.quit()
                    except: pass
        
        logging.error("❌ 所有代理均尝试失败，无法更新Cookie")
        return False

    @staticmethod
    def load_cookies():
        """加载本地Cookie"""
        if os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass
        return CookieManager.renew_cookie_with_selenium()

# ==============================================================================
# 模块二：Node.js 签名与版权接口
# ==============================================================================
class AdaptationExtractor:
    @staticmethod
    def get_signature(url_param):
        """调用 node sign_fock.js 获取签名"""
        try:
            js_path = os.path.join(SCRIPT_DIR, "sign_fock.js")
            if not os.path.exists(js_path): return None
            
            result = subprocess.run(
                ["node", "sign_fock.js", url_param],
                capture_output=True, text=True, cwd=SCRIPT_DIR, timeout=5, encoding='utf-8'
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in reversed(lines):
                    stripped = line.strip()
                    if len(stripped) == 32 and all(c in '0123456789abcdef' for c in stripped):
                        return stripped
            return None
        except Exception:
            return None

    @staticmethod
    def fetch_adaptation_info(book_id, session_cookies):
        """获取版权/改编信息"""
        if not os.path.exists(os.path.join(SCRIPT_DIR, "sign_fock.js")):
            return ""

        timestamp_sec = str(int(time.time()))
        csrf_token = session_cookies.get('_csrfToken', '')
        
        if not csrf_token:
            return ""
            
        sign_input = timestamp_sec + csrf_token
        signature = AdaptationExtractor.get_signature(sign_input)
        if not signature:
            return ""
            
        api_url = f"https://book.qidian.com/webcommon/book/getCopyRightInfo?bookId={book_id}"
        cookies_str = "; ".join([f"{k}={v}" for k, v in session_cookies.items()])
        
        headers = {
            "User-Agent": CONST_USER_AGENT,
            "Referer": f"https://book.qidian.com/info/{book_id}/",
            "X-Yuew-time": timestamp_sec,
            "X-Yuew-sign": signature,
            "Cookie": cookies_str
        }
        
        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.get(api_url, headers=headers, timeout=3, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    adaptations = []
                    info = data.get('data', {}).get('copyrightInfo', {})
                    mapping = {
                        "isHasManga": "漫画", "isHasTv": "影视", 
                        "isHasAnimation": "动画", "isHasAudio": "有声",
                        "isHasGame": "游戏", "isHasPublish": "出版"
                    }
                    for k, v in mapping.items():
                        if info.get(k):
                            adaptations.append(v)
                    result = ",".join(adaptations)
                    return result if result else "无"
        except Exception:
            pass
        return ""

# ==============================================================================
# 模块三：主爬虫逻辑 (增强解析版)
# ==============================================================================
class QidianSpider:
    def __init__(self, use_proxy=False):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': CONST_USER_AGENT,
            'Referer': 'https://www.qidian.com/'
        }
        self.use_proxy = use_proxy
        self.font_map_cache = {}
        
        # 初始化 Cookie
        cookies = CookieManager.load_cookies()
        if cookies:
            self.session.cookies.update(cookies)
            logging.info(f"✅ 已加载 {len(cookies)} 个Cookie")
        else:
            logging.warning("⚠️ 无法获取有效Cookie，部分数据可能无法抓取")
            
        # 强制设置 listStyle=2 (表格模式)
        self.session.cookies.set('listStyle', '2', domain='.qidian.com')

    def get_proxy_session(self):
        """获取带代理的Session副本"""
        s = requests.Session()
        s.headers = self.session.headers.copy()
        s.cookies = self.session.cookies.copy()
        s.cookies.set('listStyle', '2', domain='.qidian.com')
        
        # 强制禁用环境变量和系统代理注册表，以防止 urllib3 代理读取抛错 (FileNotFoundError)
        s.trust_env = False
        
        if self.use_proxy:
            proxy_str = get_user_proxy()
            if proxy_str:
                # logging.info(f"🌐 使用代理: {proxy_str}")
                s.proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
            else:
                s.proxies = {"http": None, "https": None}
        else:
            s.proxies = {"http": None, "https": None}
        return s

    def get_font_map(self, session, font_url):
        if not FONT_TOOLS_AVAILABLE: return None
        if font_url in self.font_map_cache: return self.font_map_cache[font_url]
        try:
            resp = session.get(font_url, timeout=10)
            font = TTFont(io.BytesIO(resp.content))
            cmap = font.getBestCmap()
            font.close()
            glyph_to_num = {
                'zero': '0', 'one': '1', 'two': '2', 'three': '3', 
                'four': '4', 'five': '5', 'six': '6', 'seven': '7', 
                'eight': '8', 'nine': '9', 'period': '.'
            }
            unicode_map = {code: glyph_to_num[name] for code, name in cmap.items() if name in glyph_to_num}
            self.font_map_cache[font_url] = unicode_map
            return unicode_map
        except Exception:
            return None

    def decode_text(self, text, font_map):
        if not font_map or not text: return text
        result = ""
        for char in text:
            code = ord(char)
            result += font_map.get(code, char)
        return result

    def parse_collection_number(self, text):
        """解析收藏数文本，如 '12.5万' -> 125000"""
        try:
            text = text.strip()
            if '万' in text:
                num_str = text.replace('万', '').strip()
                return int(float(num_str) * 10000)
            elif text.isdigit():
                return int(text)
            else:
                return 0
        except:
            return 0

    def fetch_collection_from_rank(self, book_title):
        """从收藏榜获取指定书籍的收藏数（通过书名匹配）"""
        # 创建新Session禁用代理，避免ProxyError
        session = requests.Session()
        session.headers = self.session.headers.copy()
        session.cookies = self.session.cookies.copy()
        session.cookies.set('listStyle', '2', domain='.qidian.com')
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        try:
            # 收藏榜共25页，每页20本，查全部500本
            for page in range(1, 26):
                if page == 1:
                    url = "https://www.qidian.com/rank/collect/"
                else:
                    url = f"https://www.qidian.com/rank/collect/page{page}/"
                
                resp = session.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                
                tree = etree.HTML(resp.text)
                
                book_names = tree.xpath('//td/a[@class="name"]/text()')
                collection_texts = tree.xpath('//td[@class="month"]/text()')
                rank_texts = tree.xpath('//td/em[@class="number"]/span/text()')
                
                for i, name in enumerate(book_names):
                    if name.strip() == book_title.strip():
                        collection_num = 0
                        rank_num = 0
                        
                        if i < len(collection_texts):
                            coll_text = collection_texts[i].strip()
                            collection_num = self.parse_collection_number(coll_text)
                        
                        if i < len(rank_texts):
                            try:
                                rank_num = int(rank_texts[i].strip())
                            except:
                                rank_num = 0
                        
                        return (collection_num, rank_num)
            
            return (0, 0)
        except:
            return (0, 0)

    def fetch_rank_page_pc_selenium(self, year, month, page):
        """使用Selenium爬取PC端月票榜（可获取100本，带字体解密）
        
        PC端分页URL格式: https://www.qidian.com/rank/yuepiao/year2026-month03-page2/
        字体反爬：月票数字使用FjgiwJie字体加密，需要解密
        """
        if not SELENIUM_AVAILABLE:
            logging.warning("Selenium不可用，无法爬取PC端月票榜")
            return []
        
        try:
            options = Options()
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--headless")
            
            browser = webdriver.Chrome(options=options)
            
            # 构建PC端分页URL
            if page == 1 and datetime.now().year == year and datetime.now().month == month:
                url = "https://www.qidian.com/rank/yuepiao/"
            else:
                url = f"https://www.qidian.com/rank/yuepiao/year{year}-month{month:02d}-page{page}/"
            
            logging.info(f"🕷️ 使用Selenium爬取PC端: {url}")
            browser.get(url)
            browser.maximize_window()
            time.sleep(3)
            
            text = browser.page_source
            browser.quit()
            
            # 提取字体URL并解密月票数字
            font_map = None
            if FONT_TOOLS_AVAILABLE:
                font_url_match = re.search(r"url\(['\"]?(https://[^'\"]+FjgiwJie\.woff[^'\"]*?)['\"]?\)", text)
                if font_url_match:
                    font_url = font_url_match.group(1).replace("'", "")
                    font_map = self.get_font_map(self.session, font_url)
                    if font_map:
                        logging.info(f"✅ 字体解密成功，映射表大小: {len(font_map)}")
            
            # 解析页面内容
            current_books = []
            
            # 提取书籍ID和标题
            pattern = r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>'
            matches = re.findall(pattern, text, re.DOTALL)
            
            # 提取月票数（使用字体解密）
            # 格式: <span class="FjgiwJie">加密数字</span></span>月票
            ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
            ticket_matches = re.findall(ticket_pattern, text)
            
            # 去重并合并数据
            seen = set()
            rank = 1
            for i, (book_id, title) in enumerate(matches):
                if book_id not in seen:
                    seen.add(book_id)
                    
                    # 解密月票数
                    tickets = 0
                    if i < len(ticket_matches) and font_map:
                        encrypted = ticket_matches[i]
                        decrypted = self.decode_text(encrypted, font_map)
                        # 提取数字
                        try:
                            tickets = int(decrypted)
                        except:
                            pass
                    
                    current_books.append({
                        'book_id': str(book_id),
                        'title': title.strip(),
                        'url': f"https://book.qidian.com/info/{book_id}",
                        'rank_on_list': rank,
                        'monthly_tickets_on_list': tickets
                    })
                    rank += 1
            
            if current_books:
                logging.info(f"✅ 【PC端Selenium模式】获取 {len(current_books)} 本书籍，月票数据已解密")
            
            return current_books
            
        except Exception as e:
            logging.error(f"Selenium爬取PC端失败: {e}")
            return []

    def fetch_rank_page_smart(self, year, month, page):
        """获取单页榜单（通过移动端 JSON 接口绕过 PC 端风控）
        
        注意：移动端分页参数不起作用，只能获取第1页的20条数据。
        如需获取更多数据，需要使用Playwright模拟滚动加载。
        """
        session = self.get_proxy_session()
        # 使用移动端 User-Agent
        mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        session.headers.update({'User-Agent': mobile_ua})
        
        def _fetch_one_page():
            # 移动端历史榜单 URL
            if page == 1 and datetime.now().year == year and datetime.now().month == month:
                url = "https://m.qidian.com/rank/yuepiao/" # 当前月第1页
            else:
                # 移动端分页格式: /rank/yuepiao/p2/ 或 /rank/yuepiao/?page=2
                url = f"https://m.qidian.com/rank/yuepiao/p{page}/"
                if datetime.now().year != year or datetime.now().month != month:
                    # 历史月份
                    url = f"https://m.qidian.com/rank/yuepiao/catid-1/{year}{month:02d}/p{page}/"
            
            resp_text = None
            
            # 对于page > 1，直接使用Playwright模拟滚动加载
            if page > 1 and PLAYWRIGHT_AVAILABLE:
                logging.info(f"🕷️ 使用Playwright模拟滚动加载获取第{page}页数据")
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        context = browser.new_context(user_agent=mobile_ua)
                        pg = context.new_page()
                        pg.goto("https://m.qidian.com/rank/yuepiao/", timeout=30000, wait_until="domcontentloaded")
                        pg.wait_for_timeout(2000)
                        
                        # 模拟滚动加载，每次滚动加载20条数据
                        scroll_times = page - 1  # 需要滚动的次数
                        for i in range(scroll_times):
                            pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            pg.wait_for_timeout(2000)  # 等待加载
                        
                        resp_text = pg.content()
                        browser.close()
                except Exception as e:
                    logging.error(f"Playwright滚动加载失败: {e}")
                    return []
            else:
                # 第1页直接请求
                try:
                    session.trust_env = False
                    resp = session.get(url, timeout=15)
                    if resp.status_code == 200:
                        resp_text = resp.text
                except Exception as e:
                    logging.warning(f"Mobile Requests 失败: {e}")

                if not resp_text and PLAYWRIGHT_AVAILABLE:
                    logging.info(f"🕷️ Mobile Requests 受阻，启用浏览器内核: {url}")
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            context = browser.new_context(user_agent=mobile_ua)
                            pg = context.new_page()
                            pg.goto(url, timeout=30000, wait_until="domcontentloaded")
                            pg.wait_for_timeout(3000)
                            resp_text = pg.content()
                            browser.close()
                    except Exception as e:
                        logging.error(f"Mobile Playwright 失败: {e}")

            if not resp_text: return []
            
            # 从 HTML 中提取嵌入的 JSON 数据
            current_books = []
            try:
                # 寻找嵌入的 JSON 脚本块
                json_match = re.search(r'id="vite-plugin-ssr_pageContext"[^>]*>(.*?)<\/script>', resp_text, re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(1))
                    # 路径：pageContext -> pageProps -> pageData -> records
                    records = json_data.get('pageContext', {}).get('pageProps', {}).get('pageData', {}).get('records', [])
                    
                    for item in records:
                        book_id = str(item.get('bid', ''))
                        if not book_id: continue
                        
                        # 解析票数 (例如 "13.47万月票")
                        rank_cnt = item.get('rankCnt', '0')
                        tickets = 0
                        ticket_match = re.search(r'(\d+\.?\d*)', rank_cnt)
                        if ticket_match:
                            tickets = float(ticket_match.group(1))
                            if '万' in rank_cnt:
                                tickets = int(tickets * 10000)
                            else:
                                tickets = int(tickets)
                        
                        current_books.append({
                            'book_id': book_id,
                            'title': item.get('bName', 'Unknown'),
                            'url': f"https://book.qidian.com/info/{book_id}",
                            'rank_on_list': item.get('rankNum', 0),
                            'monthly_tickets_on_list': tickets
                        })
                
                if current_books:
                    logging.info(f"✅ 【移动端模式】成功抓取 {len(current_books)} 本数据")
            except Exception as e:
                logging.error(f"解析移动端 JSON 失败: {e}")
                
            return current_books

        return _fetch_one_page()

    def parse_book_detail(self, book_info, year, month):
        """解析详情页"""
        session = self.get_proxy_session()
        url = book_info['url']
        
        try:
            # 优先尝试移动端获取核心数据，因为移动端防护极弱且元数据极稳
            mobile_data = self.parse_book_detail_mobile(book_info, year, month)
            if mobile_data and mobile_data.get('updated_at'):
                # 如果移动端能拿到关键的时间，我们仍然去 PC 端尝试补全字数、月票等更多维度的数据
                # 但如果 PC 端彻底失败，我们会以移动端数据为准
                pass

            resp = session.get(url, timeout=10)
            resp_text = None
            if resp.status_code == 200 and ('book-info' in resp.text or 'book-latest-chapter' in resp.text):
                resp_text = resp.text
            
            # 详情页也增加浏览器内核兜底逻辑
            if not resp_text and PLAYWRIGHT_AVAILABLE:
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        context = browser.new_context(user_agent=getattr(session, 'headers', {}).get('User-Agent', 'Mozilla/5.0'))
                        # 注入抹除痕迹脚本
                        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        pg = context.new_page()
                        pg.goto(url, timeout=30000, wait_until="domcontentloaded")
                        pg.wait_for_timeout(2000)
                        resp_text = pg.content()
                        browser.close()
                except: pass
            
            if not resp_text: return None
            # 在解析前增加微小随机休眠，平滑并发压力
            time.sleep(random.uniform(2.0, 5.0))
            tree = etree.HTML(resp_text)
            
            def get_text(xpath, default=''):
                res = tree.xpath(xpath)
                return res[0].strip() if res else default
            
            def get_num(xpath):
                txt = get_text(xpath)
                if '万' in txt: return int(float(txt.replace('万','')) * 10000)
                return int(txt) if txt.isdigit() else 0

            # 基础信息
            title = get_text('//h1/em/text()', book_info['title'])
            author = get_text('//a[@class="writer-name"]/text()', 'Unknown')
            word_count = get_num('//div[contains(@class, "book-info")]//p/em[1]/text()')
            rec_count = get_num('//cite[contains(text(), "总推荐")]/preceding-sibling::em[1]/text()')
            week_rec = get_num('//cite[contains(text(), "周推荐")]/preceding-sibling::em[1]/text()')
            
            # 状态/分类/简介
            status = get_text('//p[contains(@class, "book-attribute")]/span[1]/text()', '连载')
            if '完' in status: status = '完本'
            category = get_text('//p[contains(@class, "book-attribute")]/a[1]/text()')
            sub_category = get_text('//p[contains(@class, "book-attribute")]/a[2]/text()')
            is_vip = "VIP" if tree.xpath('//p[contains(@class, "book-attribute")]/span[contains(text(), "VIP")]') else "免费"
            is_sign = "签约" if tree.xpath('//p[contains(@class, "book-attribute")]/span[contains(text(), "签约")]') else "未签约"
            synopsis = get_text('//p[@id="book-intro-detail"]//text()')
            
            latest_chapter = ''
            updated_at = ''
            try:
                # 兼容不同版式（PC新版和部分遗留老版），以精确提取章节名和时间
                lc_node = tree.xpath('//a[contains(@class, "book-latest-chapter")]/text()')
                if not lc_node:
                    lc_node = tree.xpath('//li[contains(@class, "update")]//a[contains(@class, "blue")]/text()')
                
                time_node = tree.xpath('//span[contains(@class, "update-time")]/text()')
                if not time_node:
                    time_node = tree.xpath('//li[contains(@class, "update")]//em[contains(@class, "time")]/text()')
                
                if lc_node:
                    lc_text = lc_node[0].strip()
                    if lc_text.startswith("最新章节: "):
                        lc_text = lc_text.replace("最新章节: ", "")
                    elif lc_text.startswith("最新章节："):
                        lc_text = lc_text.replace("最新章节：", "")
                    elif lc_text.startswith("最新章节"):
                        lc_text = lc_text.replace("最新章节", "").strip()
                    latest_chapter = lc_text
                
                if time_node:
                    time_text = time_node[0].strip()
                    if time_text.startswith("更新时间:"):
                        time_text = time_text.replace("更新时间:", "")
                    elif time_text.startswith("更新时间："):
                        time_text = time_text.replace("更新时间：", "")
                    elif time_text.startswith("更新时间"):
                        time_text = time_text.replace("更新时间", "").strip()
                    updated_at = time_text
            except Exception as e: 
                pass
            
            # 月票榜排名 (从荣誉标签提取)
            monthly_ticket_rank = 0
            try:
                rank_labels = tree.xpath('//p[@class="all-label"]/a/text()')
                for label in rank_labels:
                    rank_match = re.search(r'月票.*?No\.?(\d+)', label)
                    if rank_match:
                        monthly_ticket_rank = int(rank_match.group(1))
                        break
            except: pass
            
            # 详情页实时月票数 (从 #monthCount 提取)
            detail_monthly_tickets = 0
            try:
                mt = tree.xpath('//p[@id="monthCount"]/text()')
                if mt:
                    detail_monthly_tickets = int(mt[0].strip())
                else:
                    match = re.search(r'id="monthCount"[^>]*>(\d+)<', resp.text)
                    if match:
                        detail_monthly_tickets = int(match.group(1))
            except: pass
            
            # 打赏数
            reward_count = 0
            try:
                reward_node = tree.xpath('//div[contains(@class, "reward-msg")]//span[contains(@class, "num")]/text()')
                if reward_node:
                    reward_count = int(reward_node[0].strip())
                else:
                    reward_node = tree.xpath('//span[@id="rewardNum"]/text()')
                    if reward_node:
                        reward_count = int(reward_node[0].strip())
            except: pass
            
            # 收藏数/收藏榜排名 (从收藏榜获取)
            collection_count, collection_rank = 0, 0
            try:
                collection_count, collection_rank = self.fetch_collection_from_rank(title)
            except: pass
            
            # API 获取改编信息
            adaptation_str = AdaptationExtractor.fetch_adaptation_info(
                book_info['book_id'], 
                self.session.cookies.get_dict()
            )

            data = {
                'year': year,
                'month': month,
                'novel_id': book_info['book_id'],
                'source': 'qidian',
                'title': title,
                'author': author,
                'category': category,
                'sub_category': sub_category,
                'status': status,
                'word_count': word_count,
                'recommendation_count': rec_count,
                'week_recommendation_count': week_rec,
                'is_vip': is_vip,
                'is_sign': is_sign,
                'synopsis': synopsis[:500],
                'abstract': synopsis[:500], # 同时也填入 abstract 字段
                'rank_on_list': book_info['rank_on_list'],
                'monthly_tickets_on_list': book_info['monthly_tickets_on_list'],
                'monthly_ticket_count': detail_monthly_tickets,
                'monthly_ticket_rank': monthly_ticket_rank,
                'reward_count': reward_count,
                'collection_count': collection_count,
                'collection_rank': collection_rank,
                'adaptations': adaptation_str,
                'latest_chapter': latest_chapter,
                'updated_at': updated_at,
                'crawl_time': datetime.now(),
                'cover_url': f"https://bookcover.yuewen.com/qdbimg/349573/{book_info['book_id']}/150.webp",
                'book_url': url
            }
            return data
        except Exception as e:
            # 如果 PC 端解析彻底失败，尝试最后使用移动端数据兜底
            return self.parse_book_detail_mobile(book_info, year, month)

    def parse_book_detail_mobile(self, book_info, year, month):
        """解析移动端详情页，防御更弱，结构更稳，适用于风控期回填数据"""
        session = self.get_proxy_session()
        # 移动端 URL 格式: https://m.qidian.com/book/1041162879.html
        book_id = book_info.get('book_id') or book_info.get('novel_id')
        if not book_id: return None
        
        url = f"https://m.qidian.com/book/{book_id}.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.qidian.com/'
        }
        
        try:
            # 增加一点随机延迟，避免过快
            time.sleep(random.uniform(1.0, 3.0))
            resp = session.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
                
            tree = etree.HTML(resp.text)
            
            def get_meta(prop):
                nodes = tree.xpath(f'//meta[@property="{prop}"]/@content')
                return nodes[0].strip() if nodes else ''

            title = get_meta('og:title') or book_info.get('title', 'Unknown')
            author = get_meta('og:novel:author') or 'Unknown'
            category = get_meta('og:novel:category')
            updated_at = get_meta('og:novel:update_time')
            latest_chapter = get_meta('og:novel:latest_chapter_name')
            synopsis = get_meta('og:description')
            status = get_meta('og:novel:status')
            
            return {
                'year': year,
                'month': month,
                'novel_id': book_id,
                'source': 'qidian',
                'title': title,
                'author': author,
                'category': category,
                'sub_category': '',
                'status': status or '连载',
                'word_count': 0,
                'recommendation_count': 0,
                'week_recommendation_count': 0,
                'is_vip': "未知",
                'is_sign': "未知",
                'synopsis': synopsis[:500],
                'abstract': synopsis[:500],
                'rank_on_list': book_info.get('rank_on_list', 0),
                'monthly_tickets_on_list': book_info.get('monthly_tickets_on_list', 0),
                'monthly_ticket_count': 0,
                'monthly_ticket_rank': 0,
                'reward_count': 0,
                'collection_count': 0,
                'collection_rank': 0,
                'adaptations': '',
                'latest_chapter': latest_chapter,
                'updated_at': updated_at,
                'crawl_time': datetime.now(),
                'cover_url': f"https://bookcover.yuewen.com/qdbimg/349573/{book_id}/150.webp",
                'book_url': url
            }
        except Exception as e:
            return None

# ==============================================================================
# 主执行逻辑
# ==============================================================================
def main():
    print("=" * 60)
    print("🚀 起点高级爬虫 - 集成版 v1.4 (智能补量版)")
    print("功能：自动补足数量 | 日期范围 | 并发控制 | 数据库入库")
    print("=" * 60)
    
    # 交互式输入配置
    try:
        start_str = input("请输入起始年月 (格式 YYYY-MM, 如 2023-01): ").strip()
        end_str = input("请输入结束年月 (格式 YYYY-MM, 如 2023-12): ").strip()
        
        start_date = datetime.strptime(start_str, "%Y-%m")
        end_date = datetime.strptime(end_str, "%Y-%m")
        
        if start_date > end_date:
            print("❌ 起始日期不能晚于结束日期")
            return

        limit_str = input("每月有效入库目标数量 (默认100, 输入 'all' 抓取全部): ").strip()
        if limit_str.lower() == 'all':
             target_success_count = 500
        else:
             target_success_count = int(limit_str) if limit_str else 100

        worker_str = input("并发线程数 (默认 3, 建议 2-5): ").strip()
        max_workers = int(worker_str) if worker_str else 3
        
    except ValueError:
        print("\n❌ 输入格式错误！日期请使用 YYYY-MM 格式，数字请输入纯数字。")
        return

    spider = QidianSpider(use_proxy=False)
    db = DBConnector('qidian_data') if DB_AVAILABLE else None

    # 生成月份列表
    current = start_date
    month_list = []
    while current <= end_date:
        month_list.append((current.year, current.month))
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    print(f"\n📊 任务概览：共 {len(month_list)} 个月份，每月目标有效入库 {target_success_count} 本")
    print("-" * 60)

    total_success = 0
    
    for year, month in month_list:
        print(f"\n>>> 正在处理 {year}年{month}月 ...")
        
        month_success = 0
        page = 1
        
        while month_success < target_success_count:
            if page > 25: # 起点榜单限制25页
                print("⚠️ 已达到最大页数(25页)，停止翻页。")
                break
                
            print(f"   🔎 正在扫描第 {page} 页 (当前成功: {month_success}/{target_success_count})...")
            
            books = spider.fetch_rank_page_smart(year, month, page)
            
            if not books:
                print(f"   ⚠️ 第 {page} 页无数据，可能是结束了或读取失败。")
                # 如果第一页就失败，通常是Cookie问题，fetch_rank_page_smart内部已重试过，这里直接break
                break
            
            print(f"   ✅ 获取到 {len(books)} 本，开始解析详情...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(spider.parse_book_detail, book, year, month): book['title'] 
                    for book in books
                }
                
                for future in as_completed(futures):
                    # 如果目标达成，可以选择提前退出，但为了不浪费已获取的页，通常会跑完这一页
                    if month_success >= target_success_count:
                        continue 
                        
                    title = futures[future]
                    try:
                        data = future.result()
                        if data:
                            if db: db.save_novel_monthly(data)
                            month_success += 1
                            total_success += 1
                            sys.stdout.write(f"\r     入库: {title[:10]}... (本月进度: {month_success})")
                            sys.stdout.flush()
                    except Exception as e:
                        # logging.error(f"Error processing {title}: {e}")
                        pass
            print("") # 换行
            
            page += 1
            
        print(f"✅ {year}年{month}月 完成. 实际入库: {month_success}")
        
    print("=" * 60)
    print(f"🎉 全部任务完成！总计成功入库: {total_success} 本")

if __name__ == "__main__":
    main()
