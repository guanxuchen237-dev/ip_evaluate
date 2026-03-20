import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找包含FjgiwJie的span
spans = re.findall(r'<span[^>]*class="FjgiwJie"[^>]*>([^<]*)</span>', text)
print(f'FjgiwJie spans: {len(spans)}')
print(f'Content: {spans[:5]}')

# 查找包含加密字符的完整span
# 加密字符: U+18722-U+1872D
font_unicode = [0x18722, 0x18724, 0x18725, 0x18726, 0x18727, 0x18728, 0x18729, 0x1872A, 0x1872B, 0x1872C, 0x1872D]

for code in font_unicode[:3]:
    char = chr(code)
    # 找到包含这个字符的span
    pattern = f'<span[^>]*class="FjgiwJie"[^>]*>[^<]*{char}[^<]*</span>'
    matches = re.findall(pattern, text)
    if matches:
        print(f'\nU+{code:04X} found in {len(matches)} spans')
        print(f'  Example: {matches[0]}')

# 直接搜索加密字符
print('\n=== 直接搜索加密字符 ===')
for code in font_unicode:
    char = chr(code)
    count = text.count(char)
    if count > 0:
        # 找到上下文
        idx = text.find(char)
        context = text[max(0,idx-50):idx+50]
        print(f'\nU+{code:04X} ({char}) 出现 {count} 次')
        print(f'Context: {repr(context)}')
