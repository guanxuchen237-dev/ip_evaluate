import io
from fontTools.ttLib import TTFont

# 加载本地字体文件
font_path = 'd:/ip-lumina-main-2/ip-lumina-main/scrapy/qd_iconfont.5d77e..woff'
font = TTFont(font_path)

# 获取cmap表
cmap = font.getBestCmap()
print(f'Font cmap: {len(cmap)} entries')

# 显示所有字形名称
glyph_names = set(cmap.values())
print(f'\nGlyph names (first 30): {sorted(glyph_names)[:30]}')

# 检查是否有数字相关字形
num_glyphs = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'period']
found = [g for g in num_glyphs if g in glyph_names]
print(f'\nNumber glyphs found: {found}')

# 检查是否有uni开头的字形（Unicode编码）
uni_glyphs = [g for g in glyph_names if g.startswith('uni')]
print(f'\nUnicode glyphs (first 20): {uni_glyphs[:20]}')

# 显示完整映射
print('\n=== Complete cmap (first 50) ===')
for i, (code, name) in enumerate(sorted(cmap.items())):
    if i < 50:
        char = chr(code) if code < 0x10000 else '?'
        print(f'  U+{code:04X} ({char}) -> {name}')

font.close()
