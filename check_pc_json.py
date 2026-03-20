import re
import json

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 检查所有大型script标签
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print(f'Total scripts: {len(scripts)}')

for i, script in enumerate(scripts):
    if len(script) > 500:
        print(f'\n=== Script {i} ({len(script)} chars) ===')
        # 检查是否包含JSON数据
        if '{' in script and '}' in script:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', script, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    print(f'JSON keys: {list(data.keys())[:10]}')
                    # 检查是否有书籍数据
                    if 'books' in data or 'records' in data or 'list' in data:
                        print(f'Found data key!')
                except:
                    print('Not valid JSON')
                    print(f'Preview: {script[:200]}')
