import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

def search_zongheng(title):
    search_url = f"https://search.zongheng.com/search/book?keyword={urllib.parse.quote(title)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'}
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # find the first book link
        book_div = soup.find('div', class_='search-result-list')
        if not book_div:
            return None
        book_item = book_div.find('div', class_='secd-rank-box')
        if not book_item:
            return None
        a_tag = book_item.find('a', class_='tit')
        if not a_tag:
            return None
        book_url = a_tag.get('href')
        return book_url
    except Exception as e:
        print(f"Error searching Zongheng: {e}")
        return None

def get_first_chapter_zongheng(book_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(book_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        read_btn = soup.find('a', class_='btn-read')
        if not read_btn:
             # try to find first chapter in list
             catalog = soup.find('div', class_='book-list')
             if catalog:
                 a = catalog.find('a')
                 if a:
                     return a.get('href')
             return None
        return read_btn.get('href')
    except Exception as e:
        print(f"Error get book Zongheng: {e}")
        return None

def get_chapter_content_zongheng(chapter_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(chapter_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # title
        title_tag = soup.find('div', class_='title_txtbox')
        chap_title = title_tag.text.strip() if title_tag else "第一章"
        # content
        content_div = soup.find('div', class_='content')
        if not content_div:
            return None
        paragraphs = [p.text.strip() for p in content_div.find_all('p') if p.text.strip()]
        return {"title": chap_title, "content": paragraphs}
    except Exception as e:
         print(f"Error get chapter Zongheng: {e}")
         return None

print("Testing Zongheng scraper for '无敌天命'...")
book_url = search_zongheng('无敌天命')
print(f"Book URL: {book_url}")
if book_url:
    chap_url = get_first_chapter_zongheng(book_url)
    print(f"Chapter URL: {chap_url}")
    if chap_url:
        content = get_chapter_content_zongheng(chap_url)
        if content:
            print(f"Title: {content['title']}")
            print(f"Preview: {content['content'][:3]}")
