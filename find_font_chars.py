import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找使用特定字体的span
print('=== 查找字体加密的span ===')

# 方法1：查找style包含font-family的span
font_spans = re.findall(r'<span[^>]*style="[^"]*font-family[^"]*"[^>]*>([^<]*)</span>', text)
print(f'Method 1: {len(font_spans)} spans')
if font_spans:
    print(f'Content: {font_spans[:10]}')

# 方法2：查找class包含特定字体的span
font_class = re.findall(r'<span[^>]*class="[^"]*FjgiwJie[^"]*"[^>]*>([^<]*)</span>', text)
print(f'\nMethod 2: {len(font_class)} spans')

# 方法3：查找所有包含特殊字符的span
special_chars = re.findall(r'<span[^>]*>([&#\d;]+)</span>', text)
print(f'\nMethod 3 (HTML entities): {len(special_chars)} spans')
if special_chars:
    print(f'Content: {special_chars[:10]}')

# 方法4：直接查找包含Unicode私有区字符的文本
private_area = re.findall(r'[\ue000-\uf8ff]', text)
print(f'\nMethod 4 (Unicode private area): {len(private_area)} chars')
if private_area:
    print(f'Chars: {private_area[:10]}')
