import re

# 读取两个HTML文件
with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    old_html = f.read()

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_page_new.html', 'r', encoding='utf-8') as f:
    new_html = f.read()

print(f'旧HTML长度: {len(old_html)}')
print(f'新HTML长度: {len(new_html)}')

# 检查月票数据
old_tickets = re.findall(r'<span class="FjgiwJie">([^<]+)</span></span>月票', old_html)
new_tickets = re.findall(r'<span class="FjgiwJie">([^<]+)</span></span>月票', new_html)

print(f'\n旧HTML月票: {len(old_tickets)} 条')
print(f'新HTML月票: {len(new_tickets)} 条')

# 检查差异
print('\n=== 检查关键差异 ===')

# 检查FjgiwJie出现次数
old_fj = old_html.count('FjgiwJie')
new_fj = new_html.count('FjgiwJie')
print(f'FjgiwJie出现次数: 旧={old_fj}, 新={new_fj}')

# 检查是否有月票相关class
old_ticket_class = old_html.count('class="total"')
new_ticket_class = new_html.count('class="total"')
print(f'class="total"出现次数: 旧={old_ticket_class}, 新={new_ticket_class}')

# 找到旧HTML中月票数据的完整上下文
if old_tickets:
    print(f'\n旧HTML月票示例:')
    idx = old_html.find('<span class="FjgiwJie">')
    if idx >= 0:
        context = old_html[max(0,idx-100):idx+100]
        print(context)
