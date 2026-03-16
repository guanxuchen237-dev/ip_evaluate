import requests
for b in ['剑来', '玄鉴仙族', '无敌天命', '赤心巡天', '这个魔神明明很强却过分多疑']:
    res = requests.post('http://localhost:5000/api/predict', json={'title': b, 'category': '玄幻', 'abstract': 'x'}).json()
    print(f"{b}: Score={res.get('score')} | Msg={res.get('details', {}).get('data_source')}")
