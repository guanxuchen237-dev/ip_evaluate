import re
import json

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找包含data-bid的元素结构
print('=== 检查data-bid元素结构 ===')

# 提取包含data-bid的div
bid_divs = re.findall(r'<div[^>]*data-bid="(\d+)"[^>]*>(.*?)</div>', text, re.DOTALL)
print(f'data-bid divs: {len(bid_divs)}')

# 查看第一个div的内容
if bid_divs:
    first_bid, first_content = bid_divs[0]
    print(f'\nFirst bid: {first_bid}')
    print(f'Content length: {len(first_content)}')
    print(f'Content preview: {first_content[:200]}')

# 检查__NEXT_DATA__
print('\n=== 检查JSON数据 ===')
next_data = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
if next_data:
    print(f'Found __NEXT_DATA__')
    data = json.loads(next_data.group(1))
    print(f'Keys: {list(data.keys())}')
    
    # 检查是否有书籍数据
    props = data.get('props', {}).get('initialState', {})
    print(f'initialState keys: {list(props.keys())[:10]}')
