import re

with open('zongheng_pc_debug.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 提取 name
m_name = re.search(r'"bookName":"(.*?)"', text)
print("Name:", m_name.group(1) if m_name else None)

# 提取 updateTime
m_time = re.search(r'"timeUpdate":"(.*?)"', text)
print("Time:", m_time.group(1) if m_time else None)

# 提取 latestChapter
m_chap = re.search(r'"lastChapterName":"(.*?)"', text)
print("Chapter:", m_chap.group(1) if m_chap else None)

# 提取 description
m_desc = re.search(r'"description":"(.*?)"', text)
if m_desc:
    # 可能要处理一下 unicode escape (\u554a) 或者 <br>
    desc = m_desc.group(1).encode('utf-8').decode('unicode_escape')
    # 处理 html 转义或者 <br> 等等 (如果有的话)
    desc = re.sub(r'<[^>]+>', '', desc)
    print("Desc:", desc[:100])
else:
    print("Desc: None")
