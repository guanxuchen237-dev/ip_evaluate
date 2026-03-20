import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 检查月票数据
tickets = re.findall(r'<span class="FjgiwJie">([^<]+)</span>\s*月票', text)
print(f'Saved HTML: {len(tickets)} tickets')
print(f'First 5: {tickets[:5]}')

# 检查书籍数量
books = re.findall(r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>', text, re.DOTALL)
print(f'\nBooks: {len(books)}')
print(f'First 3: {[b[1].strip() for b in books[:3]]}')
