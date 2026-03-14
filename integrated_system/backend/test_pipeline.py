import requests
# 测试地理分布 API
r = requests.get('http://localhost:5000/api/charts/geo_region')
print(f"geo_region: {r.status_code}")
d = r.json()
print(f"  regions: {len(d)}")
for item in d[:5]:
    print(f"  {item['name']}: {item['value']}")

# 测试月票排行 API
r2 = requests.get('http://localhost:5000/api/charts/ticket_top?limit=10')
print(f"\nticket_top: {r2.status_code}")
for item in r2.json():
    print(f"  [{item['platform']}] {item['title']}: {item['monthly_tickets']}")
