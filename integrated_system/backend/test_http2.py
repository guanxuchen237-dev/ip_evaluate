import requests

print("Checking Reload Endpoint...")
res = requests.post('http://localhost:5000/api/admin/reload_data')
print("Reload:", res.status_code, res.text)

res2 = requests.get('http://localhost:5000/api/library/list?page=1&pageSize=5')
data = res2.json()
print("After Reload:")
for item in data['items']:
    print(f"Title: {item['title']}, Score: {item['ip_score']}")
