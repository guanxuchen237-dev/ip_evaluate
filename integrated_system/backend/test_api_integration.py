import requests

def test_chapter_api():
    # 测试书籍标题
    title = "剑，再来！" 
    chapter_num = 1
    import urllib.parse
    encoded_title = urllib.parse.quote(title)
    url = f"http://localhost:5000/api/library/chapter?title={encoded_title}&chapter_num={chapter_num}"
    
    print(f"Requesting: {url}")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Chapter Title: {data.get('chapter_title')}")
            content = data.get('content', [])
            print(f"Content Length (Paragraphs): {len(content)}")
            if content:
                print("First Paragraph Preview:", content[0][:100])
            print(f"Source: {data.get('source')}")
            print(f"Cached: {data.get('cached')}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chapter_api()
