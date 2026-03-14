import requests
import json

try:
    res = requests.get('http://localhost:5000/api/library/list?page=1&pageSize=5')
    data = res.json()
    for item in data['items']:
        print(f"Title: {item['title']}, Score: {item['ip_score']}")
except Exception as e:
    print(f"Error: {e}")
