import urllib.request
import urllib.parse
import json

def test_qidian_chapter():
    base_url = "http://localhost:5000/api/library/chapter"
    params = {
        "title": "重生1878：美利坚头号大亨",
        "chapter_num": 2,
        "platform": "起点"
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"
    
    print(f"Testing API: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            status_code = response.getcode()
            print(f"Status Code: {status_code}")
            
            if status_code == 200:
                data = json.loads(response.read().decode('utf-8'))
                print("API Response Summary:")
                print(f"  Title: {data.get('title')}")
                print(f"  Chapter Num: {data.get('chapter_num')}")
                print(f"  Chapter Title: {data.get('chapter_title')}")
                print(f"  Source: {data.get('source')}")
                print(f"  Cached: {data.get('cached')}")
                
                content = data.get('content', [])
                if content:
                    print(f"  Content Preview: {content[0][:50]}...")
                else:
                    print("  Content is empty!")
                    
                # Basic validation
                if data.get('chapter_title') and "荒野上" in data.get('chapter_title'):
                    print("\n✅ Verification SUCCESS: Qidian chapter data retrieved correctly.")
                else:
                    print("\n❌ Verification FAILED: Chapter title did not match expected '荒野上'.")
            else:
                print(f"Error: Status {status_code}")
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_qidian_chapter()
