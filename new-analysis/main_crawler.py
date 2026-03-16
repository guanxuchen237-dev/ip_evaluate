# -*- coding: utf-8 -*-
"""
最终完美版爬虫 V2 - 字段完全对齐 - 修复变量未定义错误
"""
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient
import time
import sys
import json

# 1. 获取榜单数据
print("="*50)
print("  纵横小说数据采集系统 (Selenium稳定版)")
print("="*50)

try:
    num_str = input("请输入要爬取的书籍数量 (默认10): ").strip()
    target_count = int(num_str) if num_str else 10
except ValueError:
    print("输入无效，使用默认值 10")
    target_count = 10

print(f"\n步骤1: 获取榜单前 {target_count} 本数据...")
url = "https://www.zongheng.com/api/rank/details"
data = {"cateFineId": "0", "cateType": "21", "pageNum": "1", "pageSize": str(target_count),
        "period": "0", "rankNo": "202512", "rankType": "1", "isNewBook": "1"}
headers = {"User-Agent": "Mozilla/5.0"}

try:
    # 禁用系统代理，避免 ProxyError
    session = requests.Session()
    session.trust_env = False
    resp = session.post(url, data=data, headers=headers)
    result = resp.json()
    if result.get('code') != 0:
         print(f"API返回错误: {result}")
         sys.exit(1)
    books = result['result']['resultList']
    print(f"获取到{len(books)}本书\n")
except Exception as e:
    print(f"API请求失败: {e}")
    sys.exit(1)

# 2. 准备浏览器
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(options=options)

client = MongoClient('mongodb://localhost:27017/')
col = client['novel_analysis']['novels']

# 清空数据库
print("正在清空数据库...")
col.delete_many({})
print("✅ 数据库已清空\n")

# 3. 爬取
for i, book in enumerate(books):
    book_id = str(book['bookId'])
    name = book['bookName']
    
    # API数据映射
    status_str = '连载中' if book.get('serialStatus') == 0 else '完结'
    
    api_data = {
        'book_id': book_id,
        'novel_id': book_id,
        'rank': i + 1,  # 添加排名
        'title': name,
        'author_name': book.get('pseudonym'),
        'category_name': book.get('cateFineName'),
        'synopsis': book.get('description'),
        'status': status_str,
        'cover_url': book.get('bookCover'),
        'source_site': 'zongheng_perfect',
        'data_quality': 'perfect'
    }
    
    print(f"[{i+1}/{len(books)}] {name} (ID: {book_id})")
    
    # 进入详情页
    url = f"http://book.zongheng.com/book/{book_id}.html"
    driver.get(url)
    time.sleep(3)
    
    # 模拟点击圈子
    try:
        driver.execute_script("document.querySelector('.tab-box a[data-tab=\"quanzi\"]')?.click();")
        time.sleep(1)
    except: pass

    # JS提取
    js = """
    const data = {};
    const text = document.body.innerText;
    
    // 1. 书粉
    try {
        if (window.__NUXT__ && window.__NUXT__.state && window.__NUXT__.state.detail) {
             data.fans = window.__NUXT__.state.detail.detailBookFans?.fansScorePage?.itemCount;
        }
    } catch(e) {}
    
    // 2. DOM提取统计
    try {
        // 总推荐 (支持 "55.3万" 和 "7873" 两种格式)
        const recMatch = text.match(/([\d\.]+)\s*万总推荐/) || text.match(/(\d+)\s*总推荐/);
        if(recMatch) {
             let num = parseFloat(recMatch[1]);
             if(recMatch[0].includes('万')) num *= 10000;
             data.totalRec = Math.round(num);
        }
        
        const weekRecMatch = text.match(/(\\d+)\\s*周推荐/);
        if(weekRecMatch) data.weekRec = parseInt(weekRecMatch[1]);
        
        // 点击
        const clickMatch = text.match(/([\\d\\.]+)\\s*万总点击/) || text.match(/(\d+)\s*总点击/);
        if(clickMatch) {
             let num = parseFloat(clickMatch[1]);
             if(clickMatch[0].includes('万')) num *= 10000;
             data.click = Math.round(num);
        }
        
        // 字数
        const wordMatch = text.match(/([\\d\\.]+)\\s*万字数/) || text.match(/(\d+)\s*字数/);
        if(wordMatch) {
             let num = parseFloat(wordMatch[1]);
             if(wordMatch[0].includes('万')) num *= 10000;
             data.words = Math.round(num);
        }
        
    } catch(e) {}
    
    // 3. 月票
    try {
        const monthEl = document.querySelector('.support-works--month .num');
        if(monthEl) {
            data.month = parseInt(monthEl.innerText);
        } else {
             const m = text.match(/(\\d+)\\s*本月票数/);
             if(m) data.month = parseInt(m[1]);
        }
    } catch(e) {}
    
    // 4. 签约状态 (修复：全文匹配)
    if (text.includes('已签约')) {
        data.contract = '已签约';
    } else if (text.includes('未签约')) {
        data.contract = '未签约';
    } else {
        data.contract = '未知';
    }
    
    // 5. 捧场
    try {
        const rewardM = text.match(/捧场\\s*(\\d+)\\s*本月/);
        if(rewardM) data.reward = parseInt(rewardM[1]);
    } catch(e) {}
    
    return data;
    """
    
    try:
        page_stats = driver.execute_script(js)
    except Exception as e:
        page_stats = {}

    # 初始化 final_data
    final_data = api_data.copy()

    final_data['fans_count'] = page_stats.get('fans', 0)
    final_data['total_recommendation_count'] = page_stats.get('totalRec', 0)
    final_data['week_recommendation_count'] = page_stats.get('weekRec', 0)
    final_data['click_count'] = page_stats.get('click', 0)
    final_data['total_words'] = page_stats.get('words', 0)
    final_data['monthly_ticket_count'] = page_stats.get('month', 0)
    final_data['reward_count'] = page_stats.get('reward', 0)
    final_data['contract_status'] = page_stats.get('contract', '未知') # 补全签约状态
    final_data['crawl_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
    final_data['ranking_lists'] = [{'rank_name': '月票榜', 'rank_position': i+1}]

    print(f"  状态: {final_data['status']} | 签约: {final_data['contract_status']}")
    print(f"  数据: 点击={final_data['click_count']}, 字数={final_data['total_words']}")
    
    col.update_one({'book_id': book_id}, {'$set': final_data}, upsert=True)
    print("  ✅ 保存成功\n")

driver.quit()

# 清理冗余字段 serial_status
print("\n正在清理旧的冗余字段 serial_status...")
col.update_many({}, {'$unset': {'serial_status': ""}})
print("✅ 清理完成")

client.close()
print("全部完成！")
