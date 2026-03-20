import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 检查月票数据
ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
tickets = re.findall(ticket_pattern, text)
print(f'保存的HTML月票数据: {len(tickets)} 条')

# 检查是否有JavaScript渲染的迹象
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print(f'Script标签数: {len(scripts)}')

# 检查是否有__NEXT_DATA__
next_data = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
if next_data:
    print('有__NEXT_DATA__')
else:
    print('无__NEXT_DATA__')

# 检查页面标题
title = re.search(r'<title>([^<]+)</title>', text)
if title:
    print(f'页面标题: {title.group(1)}')

# 检查是否是完整的渲染页面
if 'FjgiwJie' in text:
    print('包含FjgiwJie字体class - 这是渲染后的页面')
else:
    print('不包含FjgiwJie - 可能是初始HTML')
