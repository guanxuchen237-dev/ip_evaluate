import re
import io
import os
import urllib.request
from fontTools.ttLib import TTFont

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 下载字体
font_url = "https://qdfepccdn.qidian.com/gtimg/qd_anti_spider/FjgiwJie.woff"
req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
font = TTFont(io.BytesIO(resp.read()))

# 获取glyf表
glyf = font.get('glyf')
cmap = font.getBestCmap()

print('=== 字形轮廓分析 ===')
glyph_to_num = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 
    'four': '4', 'five': '5', 'six': '6', 'seven': '7', 
    'eight': '8', 'nine': '9', 'period': '.'
}

# 检查每个数字字形的轮廓
for code, name in cmap.items():
    if name in glyph_to_num:
        glyph = glyf[name]
        # 获取轮廓点数
        if hasattr(glyph, 'coordinates') and glyph.coordinates:
            print(f'{name} -> {glyph_to_num[name]}: {len(glyph.coordinates)} points')

font.close()

# 检查PC端HTML中的实际Unicode字符
print('\n=== PC端HTML中的加密字符 ===')
with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 找到所有Unicode私有区字符
private_chars = re.findall(r'[\ue000-\uf8ff]', text)
print(f'Private area chars: {len(private_chars)}')
print(f'Unique: {set(private_chars)}')

# 检查这些字符周围的上下文
for char in set(private_chars)[:5]:
    idx = text.find(char)
    context = text[max(0,idx-50):idx+50]
    print(f'\n{char} (U+{ord(char):04X}) context:')
    print(context.replace('\n', ' '))
