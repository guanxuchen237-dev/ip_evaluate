import io
import os
import urllib.request
from fontTools.ttLib import TTFont

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 下载PC端实际使用的字体
font_url = "https://qdfepccdn.qidian.com/gtimg/qd_anti_spider/FjgiwJie.woff"
print(f'Downloading: {font_url}')

req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
font_data = resp.read()

# 保存字体文件
with open('d:/ip-lumina-main-2/ip-lumina-main/scrapy/FjgiwJie.woff', 'wb') as f:
    f.write(font_data)
print(f'Saved: scrapy/FjgiwJie.woff')

# 分析字体
font = TTFont(io.BytesIO(font_data))
cmap = font.getBestCmap()
print(f'\nFont cmap: {len(cmap)} entries')

# 显示所有字形名称
glyph_names = set(cmap.values())
print(f'Glyph names: {sorted(glyph_names)}')

# 检查数字字形
num_glyphs = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'period']
found = [g for g in num_glyphs if g in glyph_names]
print(f'\nNumber glyphs found: {found}')

# 建立映射
glyph_to_num = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 
    'four': '4', 'five': '5', 'six': '6', 'seven': '7', 
    'eight': '8', 'nine': '9', 'period': '.'
}

print('\n=== Unicode to Number Mapping ===')
unicode_map = {}
for code, name in cmap.items():
    if name in glyph_to_num:
        unicode_map[code] = glyph_to_num[name]
        print(f'  U+{code:04X} -> {glyph_to_num[name]}')

font.close()

# 测试解密PC端HTML中的加密字符
print('\n=== 测试解密PC端加密字符 ===')
encrypted_chars = ['\ue61f', '\ue60c', '\ue60d', '\ue642', '\ue62f']
print(f'PC端加密字符: {[hex(ord(c)) for c in encrypted_chars]}')

# 检查PC端HTML中的实际加密字符
with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 找到包含加密字符的上下文
import re
for char in encrypted_chars[:3]:
    idx = text.find(char)
    if idx >= 0:
        context = text[max(0,idx-30):idx+30]
        print(f'\n{hex(ord(char))} context: {repr(context)}')
