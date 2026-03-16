import re, json

with open('zongheng_pc_debug.html', 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'window\.__NUXT__=(.*?);</script>', content)
if m:
    data = json.loads(m.group(1))
    
    # print keys
    try:
        book_info = data['state']['bookDetails']['bookInfo']
        print("Title:", book_info.get('bookName'))
        print("Updated At:", book_info.get('timeUpdate'))
        print("Latest Chapter:", book_info.get('lastChapterName'))
        print("Abstract:", book_info.get('description'))
        print("SUCCESS")
    except Exception as e:
        print("Error accessing nested dict:", e)
        # 宽泛搜索
        def find_keys(obj, k):
            if isinstance(obj, dict):
                for key, val in obj.items():
                    if key == k: print(f"Found {k}:", val)
                    find_keys(val, k)
            elif isinstance(obj, list):
                for i in obj: find_keys(i, k)
        
        find_keys(data, 'timeUpdate')
        find_keys(data, 'description')
