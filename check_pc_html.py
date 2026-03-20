import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 检查data-bid分布
bids = re.findall(r'data-bid="(\d+)"', text)
print(f'Total data-bid: {len(bids)}, Unique: {len(set(bids))}')

# 检查书籍名称
names = re.findall(r'<h4[^>]*><a[^>]*>([^<]+)</a></h4>', text)
print(f'Book names (h4>a): {len(names)}')
if names:
    print(f'First 5: {names[:5]}')

# 检查其他选择器
names2 = re.findall(r'class="book-name"[^>]*>([^<]+)<', text)
print(f'Book names (book-name): {len(names2)}')

# 检查月票数
tickets = re.findall(r'(\d+)月票', text)
print(f'Tickets: {len(tickets)}, first 5: {tickets[:5]}')

# 检查排名
ranks = re.findall(r'<span[^>]*class="rank[^"]*"[^>]*>(\d+)</span>', text)
print(f'Ranks: {len(ranks)}')
