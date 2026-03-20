import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找书籍和月票的组合结构
print('=== 书籍和月票结构 ===')

# 先找到第一个书籍的完整HTML块
first_book = re.search(r'data-bid="(\d+)"[^>]*>.*?</div>\s*</div>', text[:10000], re.DOTALL)
if first_book:
    block = first_book.group(0)
    print(f'First book block length: {len(block)}')
    print(f'\nBlock preview:\n{block[:500]}')
    
    # 在块内查找月票
    ticket_match = re.search(r'月票[^\d]*(\d+)', block)
    if ticket_match:
        print(f'\nTicket found: {ticket_match.group(1)}')
    else:
        print('\nNo ticket found in block')
        
# 查找所有月票相关文本
print('\n=== 月票文本 ===')
ticket_texts = re.findall(r'月票[^\d<]*([^\s<]+)', text)
print(f'Ticket texts: {ticket_texts[:10]}')
