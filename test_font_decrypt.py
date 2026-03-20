import re
import io
import os
import urllib.request
from fontTools.ttLib import TTFont

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 下载字体
font_url = "https://qdfepccdn.qidian.com/gtimg/qd_anti_spider/FjgiwJie.woff"
req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
font = TTFont(io.BytesIO(resp.read()))
cmap = font.getBestCmap()
font.close()

print(f'Font cmap: {len(cmap)} entries')

# 建立Unicode到数字的映射
glyph_to_num = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 
    'four': '4', 'five': '5', 'six': '6', 'seven': '7', 
    'eight': '8', 'nine': '9', 'period': '.'
}

unicode_map = {}
for code, name in cmap.items():
    if name in glyph_to_num:
        unicode_map[code] = glyph_to_num[name]
        print(f'  U+{code:04X} ({chr(code)}) -> {glyph_to_num[name]}')

print(f'\nMapping: {unicode_map}')

# 测试解密
test_chars = ['\ue61f', '\ue60c', '\ue60d', '\ue642', '\ue62f']
print(f'\nTest decryption:')
for c in test_chars:
    code = ord(c)
    decrypted = unicode_map.get(code, c)
    print(f'  {c} (U+{code:04X}) -> {decrypted}')
