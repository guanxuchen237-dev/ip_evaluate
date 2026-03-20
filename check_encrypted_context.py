import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 找到包含加密字符的完整文本块
print('=== 加密字符上下文 ===')

# 找到所有包含Unicode私有区字符的文本
private_area_pattern = r'[^\x00-\xffff]'
matches = re.findall(r'.{100}' + private_area_pattern + r'.{100}', text, re.DOTALL)

print(f'Found {len(matches)} contexts')
for i, m in enumerate(matches[:3]):
    print(f'\nContext {i+1}:')
    # 只显示可打印字符
    clean = ''.join(c if c.isprintable() else f'[{ord(c):04X}]' for c in m)
    print(clean[:200])
