import re
import json

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available")

if PLAYWRIGHT_AVAILABLE:
    mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    
    print('Testing Playwright scroll loading...')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=mobile_ua)
        pg = context.new_page()
        pg.goto("https://m.qidian.com/rank/yuepiao/", timeout=30000, wait_until="domcontentloaded")
        pg.wait_for_timeout(2000)
        
        # 获取初始数据
        text = pg.content()
        print(f'Page length: {len(text)}')
        
        json_match = re.search(r'id="vite-plugin-ssr_pageContext"[^>]*>(.*?)</script>', text, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
            records = json_data.get('pageContext', {}).get('pageProps', {}).get('pageData', {}).get('records', [])
            print(f'Initial records: {len(records)}')
        else:
            print('No JSON found in initial page')
        
        # 滚动一次
        print('Scrolling...')
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(3000)
        
        # 获取滚动后数据
        text = pg.content()
        print(f'After scroll page length: {len(text)}')
        
        json_match = re.search(r'id="vite-plugin-ssr_pageContext"[^>]*>(.*?)</script>', text, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
            records = json_data.get('pageContext', {}).get('pageProps', {}).get('pageData', {}).get('records', [])
            print(f'After scroll records: {len(records)}')
            if records:
                print(f'First: {records[0].get("bName")}')
                print(f'Last: {records[-1].get("bName")}')
        else:
            print('No JSON found after scroll')
        
        browser.close()
else:
    print('Playwright not available')
