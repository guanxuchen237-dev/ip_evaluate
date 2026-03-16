import re
import html

text = open('zh_test.html', encoding='utf-8').read()

m_img = re.search(r'(?:property|name)="og:image"\s*content="([^"]+)"', text)
print('IMG:', m_img.group(1) if m_img else None)

m_abs = re.search(r'(?:property|name)="og:description"\s*content="([^"]+)"', text)
if m_abs:
    a = m_abs.group(1)
    a = html.unescape(a)
    if a.startswith('content="'):
        a = a.replace('content="', '', 1)
        if a.endswith('"'):
            a = a[:-1]
    if '观看小说：' in a:
        a = a.split('观看小说：')[-1].strip()
    print('ABS:', a)
else:
    print('ABS: None')

m_chap = re.search(r'(?:property|name)="og:novel:latest_chapter_name"\s*content="([^"]+)"', text)
print('CHAP:', m_chap.group(1) if m_chap else None)
