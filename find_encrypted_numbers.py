import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 检查是否包含字体映射中的Unicode字符 (U+18722 = 𘜢)
# 这些是真正的数字加密字符
print('=== 检查PC端HTML中的数字加密字符 ===')

# 字体映射中的Unicode
font_unicode = [0x18722, 0x18724, 0x18725, 0x18726, 0x18727, 0x18728, 0x18729, 0x1872A, 0x1872B, 0x1872C, 0x1872D]

for code in font_unicode:
    char = chr(code)
    count = text.count(char)
    if count > 0:
        print(f'U+{code:04X} ({char}) 出现 {count} 次')
        # 显示上下文
        idx = text.find(char)
        context = text[max(0,idx-20):idx+20]
        print(f'  Context: {repr(context)}')

# 检查月票相关区域
print('\n=== 检查月票区域 ===')
# 找到第一个书籍的完整HTML块
book_blocks = re.findall(r'<div class="book-img-text[^>]*>.*?</div>\s*</div>', text[:50000], re.DOTALL)
print(f'Found {len(book_blocks)} book blocks')

if book_blocks:
    print(f'\nFirst book block length: {len(book_blocks[0])}')
    # 检查是否包含加密数字
    block = book_blocks[0]
    for code in font_unicode:
        char = chr(code)
        if char in block:
            print(f'Found encrypted number: {char} (U+{code:04X})')
