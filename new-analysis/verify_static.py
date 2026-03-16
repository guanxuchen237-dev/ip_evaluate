import requests
import re
import json

url = "http://book.zongheng.com/book/1336976.html"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

print("正在请求页面...")
try:
    resp = requests.get(url, headers=headers, timeout=10)
    html = resp.text
    
    print(f"页面大小: {len(html)} chars")
    
    # 1. 检查Nuxt数据
    if "window.__NUXT__" in html:
        print("✅ 发现 window.__NUXT__")
    else:
        print("❌ 未发现 window.__NUXT__")
        
    # 2. 检查总推荐 (静态文本)
    if "总推荐" in html:
        print("✅ 发现 '总推荐' 文本")
        # 尝试正则提取
        m = re.search(r'([\d\.]+)\s*万?总推荐', html)
        if m:
            print(f"   提取到: {m.group(0)}")
    else:
        print("❌ 未发现 '总推荐' 文本")
        
    # 3. 检查签约状态
    if "已签约" in html:
        print("✅ 发现 '已签约'")
    else:
        print("❌ 未发现 '已签约'")

except Exception as e:
    print(f"请求失败: {e}")
