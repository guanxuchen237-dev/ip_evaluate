import urllib.parse
import requests

def test_jianlai():
    title = "剑来"
    chapter_num = 1
    encoded_title = urllib.parse.quote(title)
    url = f"http://localhost:5000/api/library/chapter?title={encoded_title}&chapter_num={chapter_num}"
    
    print(f"Requesting: {url}")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Source: {data.get('source')}")
        print(f"Cached: {data.get('cached')}")
        print(f"Debug Title Repr: {data.get('_debug_title_repr')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_jianlai()
