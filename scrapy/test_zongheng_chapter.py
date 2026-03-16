import requests
from lxml import etree

def test_zongheng():
    # 测试目录页
    novel_id = "1336976"  # 例: 剑来, 或者其它
    catalog_url = f"https://book.zongheng.com/showchapter/{novel_id}.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetch catalog: {catalog_url}")
    res = requests.get(catalog_url, headers=headers)
    
    if "纵横中文网验证码" in res.text or "\\u9a8c\\u8bc1\\u7801" in res.text:
       print("Banned by CAPTCHA.")
       return
       
    html = etree.HTML(res.text)
    links = html.xpath('//li[contains(@class, "col-4")]/a/@href')
    print("Catalog links found:", len(links))
    if links:
        print("Sample link:", links[0])
        
        # 测试第二章内容请求
        print(f"\nFetch chapter: {links[0]}")
        chap_res = requests.get(links[0], headers=headers)
        chap_html = etree.HTML(chap_res.text)
        
        title_nodes = chap_html.xpath('//div[@class="title_txtbox"]/text() | //h1/text() | //div[@class="title"]/text() | //div[contains(@class,"title")]/text()')
        print("Title extracted:", "".join([t.strip() for t in title_nodes if t.strip()]))
        
        content_nodes = chap_html.xpath('//div[@class="content"]/p/text() | //div[contains(@class, "reader-content")]//p/text() | //div[@id="readerFs"]//p/text()')
        content = "\\n".join([p.strip() for p in content_nodes if p.strip()])
        print("Content length:", len(content))
        print("Preview:", content[:100])
    else:
        print("No links found. Here's partial HTML:", res.text[:500])

if __name__ == '__main__':
    test_zongheng()
