import re
import os
import asyncio
from playwright.async_api import async_playwright

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 设置User-Agent
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
        })
        
        print('访问页面...')
        await page.goto('https://www.qidian.com/rank/yuepiao/', wait_until='networkidle')
        
        # 等待页面渲染
        print('等待5秒...')
        await page.wait_for_timeout(5000)
        
        text = await page.content()
        
        # 检查月票数据
        ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
        tickets = re.findall(ticket_pattern, text)
        print(f'\n加密月票数据: {len(tickets)} 条')
        
        # 检查书籍
        books = re.findall(r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>', text, re.DOTALL)
        print(f'书籍: {len(books)} 本')
        
        if tickets:
            print(f'前5个月票: {tickets[:5]}')
        
        # 保存HTML
        with open('d:/ip-lumina-main-2/ip-lumina-main/pc_playwright.html', 'w', encoding='utf-8') as f:
            f.write(text)
        print('已保存到 pc_playwright.html')
        
        await browser.close()

asyncio.run(main())
