import requests
import re

session = requests.Session()
session.trust_env = False
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.zongheng.com/rank',
}
resp = session.get('https://book.zongheng.com/book/1385191.html', headers=HEADERS, timeout=10, verify=False)
text = resp.text

print("Length:", len(text))
print("Title:", re.search(r'<title>(.*?)</title>', text).group(1) if re.search(r'<title>(.*?)</title>', text) else 'Not Found')
print("--- OG PROPERTIES ---")
og_matches = re.findall(r'property="og:([^"]+)"\s*content="([^"]+)"', text)
for og in og_matches:
    print(og)

print("\n--- Fallback Image ---")
img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]+class="book-img"', text)
print(img_m.group(1) if img_m else 'None')

print("\n--- Fallback Abstract ---")
abs_m = re.search(r'class="book-dec[^>]*>.*?<p>(.*?)</p>', text, re.DOTALL)
print(abs_m.group(1).strip() if abs_m else 'None')

print("\n--- Fallback Chapter ---")
chap_m = re.search(r'class="tit"\s+target="_blank"\s+title="([^"]+)"', text)
print(chap_m.group(1) if chap_m else 'None')
