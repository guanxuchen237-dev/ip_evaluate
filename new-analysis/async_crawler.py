# -*- coding: utf-8 -*-
"""
高性能异步爬虫 - 30本小说并发采集
集成IP代理池 + 静态页面解析 (无需Selenium)
"""
import asyncio
import aiohttp
import requests
import re
import json
import time
from datetime import datetime
from pymongo import MongoClient
from proxy_pool import ProxyPool

# 配置
TARGET_COUNT = 30  # 目标爬取数量
CONCURRENCY = 5    # 并发数
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'novel_analysis'
COL_NAME = 'novels'

class AsyncNovelCrawler:
    def __init__(self):
        self.proxy_pool = ProxyPool()
        self.client = MongoClient(MONGO_URI)
        self.col = self.client[DB_NAME][COL_NAME]
        
    async def get_rank_list(self):
        """获取榜单前30名"""
        print(f"步骤1: 获取榜单前{TARGET_COUNT}本...")
        url = "https://www.zongheng.com/api/rank/details"
        data = {
            "cateFineId": "0", "cateType": "21", "pageNum": "1", 
            "pageSize": str(TARGET_COUNT), "period": "0", 
            "rankNo": "202512", "rankType": "1", "isNewBook": "1"
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            books = resp.json()['result']['resultList']
            print(f"✅ 获取到{len(books)}本书籍信息\n")
            return books
        except Exception as e:
            print(f"❌ 榜单API请求失败: {e}")
            return []

    async def fetch_detail(self, session, book):
        """异步获取详情页数据"""
        book_id = str(book['bookId'])
        url = f"http://book.zongheng.com/book/{book_id}.html"
        proxy = self.proxy_pool.get_proxy()
        
        if not proxy:
            print("⚠️ 无可用代理，尝试直连...")
            proxy_url = None
        else:
            # 修复: 从 _info 中获取IP和端口
            info = proxy.get('_info', {})
            if not info:
                 # 兼容直接返回字典的情况
                 info = proxy
            proxy_url = f"http://{info.get('ip')}:{info.get('port')}"

        try:
            async with session.get(url, proxy=proxy_url, timeout=10) as response:
                if response.status != 200:
                    self.proxy_pool.mark_failed(proxy)
                    return None
                    
                html = await response.text()
                return self.parse_detail(html, book, i_rank=book.get('rank', 0))
                
        except Exception as e:
            # print(f"  ❌ 抓取失败 {book['bookName']}: {e}")
            if proxy:
                self.proxy_pool.mark_failed(proxy)
            return None

    def parse_detail(self, html, book, i_rank):
        """解析静态HTML (直接提取window.__NUXT__和正则)"""
        try:
            # 基础数据
            status_str = '连载中' if book.get('serialStatus') == 0 else '完结'
            data = {
                'book_id': str(book['bookId']),
                'novel_id': str(book['bookId']),
                'rank': i_rank,
                'title': book['bookName'],
                'author_name': book.get('pseudonym'),
                'category_name': book.get('cateFineName'),
                'synopsis': book.get('description'),
                'status': status_str,
                'cover_url': book.get('bookCover'),
                'source_site': 'zongheng_async',
                'crawl_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 1. 提取Nuxt数据 (包含书粉)
            fans_count = 0
            nuxt_match = re.search(r'window\.__NUXT__=(.*?);', html)
            if nuxt_match:
                try:
                    # 这是一段JS代码，简单的可以用json解析，复杂的可能需要execjs
                    # 为简便，这里用正则提取关键字段
                    fans_m = re.search(r'itemCount:(\d+)', nuxt_match.group(1))
                    if fans_m:
                        fans_count = int(fans_m.group(1))
                except: pass
            data['fans_count'] = fans_count

            # 2. 正则提取统计数据 (穿透HTML标签)
            def extract_num(pattern, text):
                # pattern示例: r'>([\d\.]+)<.*?万?总推荐'
                m = re.search(pattern, text, re.DOTALL)
                if m:
                    num_str = m.group(1)
                    num = float(num_str)
                    # 检查是否包含"万" (在整个匹配串中查找)
                    if '万' in m.group(0):
                        num *= 10000
                    return int(round(num))
                return 0

            # 总推荐: >7876</span> <i data-v-01291c41>总推荐
            # 或 >55.3</span> <i data-v-01291c41>万总推荐
            rec_pattern = r'>([\d\.]+)<.*?万?总推荐'
            data['total_recommendation_count'] = extract_num(rec_pattern, html)
            
            # 周推荐
            week_pattern = r'>(\d+)<.*?周推荐'
            data['week_recommendation_count'] = extract_num(week_pattern, html)
            
            # 点击
            click_pattern = r'>([\d\.]+)<.*?万?总点击'
            data['click_count'] = extract_num(click_pattern, html)
            
            # 字数
            word_pattern = r'>([\d\.]+)<.*?万?字数'
            data['total_words'] = extract_num(word_pattern, html)

            # 月票 (静态页可能不显示，但如果有的话)
            month_pattern = r'>(\d+)<.*?本月票数'
            data['monthly_ticket_count'] = extract_num(month_pattern, html)
            
            # 签约状态
            if '已签约' in html:
                data['contract_status'] = '已签约'
            elif '未签约' in html:
                data['contract_status'] = '未签约'
            else:
                data['contract_status'] = '未知'

            return data

        except Exception as e:
            print(f"解析错误: {e}")
            return None

    async def run(self):
        # 0. 清空数据库
        print("正在清空数据库...")
        self.col.delete_many({})
        print("✅ 数据库已清空")

        # 1. 获取榜单
        books = await self.get_rank_list()
        if not books: return
        
        # 给books加上rank
        for i, b in enumerate(books):
            b['rank'] = i + 1

        print(f"步骤2: 启动异步采集 (并发={CONCURRENCY})...\n")
        
        # 2. 异步采集
        tasks = []
        timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(limit=CONCURRENCY)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for book in books:
                tasks.append(self.fetch_detail(session, book))
            
            results = await asyncio.gather(*tasks)
            
        # 3. 结果处理
        success_count = 0
        for res in results:
            if res:
                # 打印简报
                print(f"[{res['rank']}/{TARGET_COUNT}] {res['title']} - 点击:{res['click_count']} 月票:{res['monthly_ticket_count']}")
                self.col.update_one({'book_id': res['book_id']}, {'$set': res}, upsert=True)
                success_count += 1
            else:
                print(f"  ❌ 失败")

        print(f"\n全部完成！成功: {success_count}/{TARGET_COUNT}")

if __name__ == "__main__":
    crawler = AsyncNovelCrawler()
    asyncio.run(crawler.run())
