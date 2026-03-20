import re
import io
import os
import urllib.request

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

try:
    from fontTools.ttLib import TTFont
    FONT_TOOLS_AVAILABLE = True
except ImportError:
    FONT_TOOLS_AVAILABLE = False
    print("fonttools not available")

if FONT_TOOLS_AVAILABLE:
    # 从PC端HTML提取字体URL
    with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 提取字体URL
    font_urls = re.findall(r"url\(['\"]?(https://[^'\"]+\.woff[^'\"]*?)['\"]?\)", text)
    if font_urls:
        font_url = font_urls[0].replace("'", "")
        print(f'Font URL: {font_url}')
        
        # 下载字体
        req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        font = TTFont(io.BytesIO(resp.read()))
        cmap = font.getBestCmap()
        font.close()
        
        print(f'\nFont cmap entries: {len(cmap)}')
        
        # 显示字形名称
        glyph_names = set(cmap.values())
        print(f'\nGlyph names: {sorted(glyph_names)[:20]}')
        
        # 检查是否有数字字形
        num_glyphs = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'period']
        found = [g for g in num_glyphs if g in glyph_names]
        print(f'\nNumber glyphs found: {found}')
        
        # 检查是否有汉字字形
        chinese_glyphs = [g for g in glyph_names if g.startswith('uni') or g.startswith('glyph')]
        print(f'\nOther glyphs (first 10): {sorted(chinese_glyphs)[:10]}')
