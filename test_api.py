import urllib.request
import json

# 测试实时追踪 API
print("=== 实时追踪 API 测试 ===\n")

# 测试捞尸人 - 需要URL编码
title = '%E6%8D%9E%E5%B0%B8%E4%BA%BA'  # 捞尸人的URL编码
url = f'http://localhost:5000/api/admin/realtime_tracking?source=qidian&title={title}'
try:
    with urllib.request.urlopen(url) as res:
        data = json.loads(res.read().decode())
        print(f"捞尸人:")
        print(f"  title: {data.get('title')}")
        print(f"  dates: {len(data.get('dates', []))}")
        print(f"  monthly_tickets: {len(data.get('monthly_tickets', []))}")
        if data.get('dates'):
            print(f"  前3条数据:")
            for i in range(min(3, len(data['dates']))):
                print(f"    {data['dates'][i]}: {data['monthly_tickets'][i]}")
        else:
            print("  无数据")
except Exception as e:
    print(f"错误: {e}")
