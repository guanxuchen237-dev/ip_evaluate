import io
from fontTools.ttLib import TTFont

# 加载本地字体文件
font_path = 'd:/ip-lumina-main-2/ip-lumina-main/scrapy/font.woff2'
font = TTFont(font_path)

# 获取cmap表
cmap = font.getBestCmap()
print(f'Font cmap: {len(cmap)} entries')

# 显示所有字形名称
glyph_names = set(cmap.values())
print(f'\nGlyph names: {sorted(glyph_names)}')

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
for code, name in sorted(cmap.items()):
    if name in glyph_to_num:
        unicode_map[code] = glyph_to_num[name]
        char = chr(code) if code < 0x10000 else '?'
        print(f'  U+{code:04X} ({char}) -> {glyph_to_num[name]}')

font.close()

print(f'\nTotal mapped: {len(unicode_map)} characters')

# 测试解密PC端HTML中的加密字符
print('\n=== 测试解密PC端加密字符 ===')
# PC端HTML中的加密字符 (来自FjgiwJie字体)
encrypted_chars = ['\ue61f', '\ue60c', '\ue60d', '\ue642', '\ue62f']
print(f'PC端加密字符: {[hex(ord(c)) for c in encrypted_chars]}')

# PC端月票加密字符 (来自find_encrypted_numbers.py)
# U+18722 (𘜢) 等
print('\nPC端月票加密字符 (来自FjgiwJie):')
for code in [0x18722, 0x18724, 0x18725, 0x18726, 0x18727, 0x18728, 0x18729, 0x1872A, 0x1872B, 0x1872C, 0x1872D]:
    char = chr(code)
    decrypted = unicode_map.get(code, '?')
    print(f'  U+{code:04X} ({char}) -> {decrypted}')
