import re

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找字体family
fonts = re.findall(r'font-family:\s*([^\;]+)', text)
print(f'Font families: {set(fonts)}')

# 查找字体URL
urls = re.findall(r"url\(['\"]?([^'\")]+\.woff[^)]*)", text)
print(f'\nFont URLs: {urls[:5]}')

# 查找@font-face定义
font_faces = re.findall(r'@font-face\s*\{[^}]+\}', text, re.DOTALL)
print(f'\n@font-face definitions: {len(font_faces)}')
for i, ff in enumerate(font_faces):
    print(f'\nFont face {i}:')
    print(ff[:200])
