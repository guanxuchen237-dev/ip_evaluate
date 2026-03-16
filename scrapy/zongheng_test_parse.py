import re
from lxml import etree

def analyze_zongheng():
    try:
        with open('zongheng_debug.html', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print("--- OG Meta Tags ---")
    og_patterns = [
        'og:title', 'og:novel:author', 'og:novel:category', 
        'og:novel:update_time', 'og:novel:latest_chapter_name', 'og:description'
    ]
    for prop in og_patterns:
        # 纵横使用的是 name="og:..." 而非 property="og:..."
        match = re.search(f'name="?{prop}"?[^>]*content="?([^">]*)', content)
        if match:
            print(f"{prop}: {match.group(1)}")
        else:
            print(f"{prop}: Not found")

    print("\n--- XPath Analysis ---")
    tree = etree.HTML(content)
    # 纵横 PC 版新版结构 (Nuxt SSR)
    xpaths = {
        'title': '//div[contains(@class, "book-info--title")]/span/text()',
        'author': '//span[contains(@class, "cateFineId")]/following-sibling::span[1]/text()',
        'latest_chapter': '//div[contains(@class, "book-info--chapter-name")]/a/text()',
        'update_time': '//div[contains(@class, "book-info--chapter")]/div[2]/span/text()',
    }
    for label, xpath in xpaths.items():
        res = tree.xpath(xpath)
        print(f"{label}: {res[0].strip() if res else 'Not found'}")

if __name__ == "__main__":
    analyze_zongheng()
