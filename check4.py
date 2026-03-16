import sys; sys.path.insert(0, 'd:/ip-lumina-main/integrated_system/backend')
from data_manager import data_manager

for b in ['剑来', '玄鉴仙族', '无敌天命', '赤心巡天', '这个魔神明明很强却过分多疑']:
    rows = data_manager.df[data_manager.df['title'].str.contains(b, na=False)]
    if not rows.empty:
        for _, r in rows.iterrows():
            print(f"{b} [{r.get('year')}-{r.get('month')}]: Score={r['IP_Score']}, fin={r['finance']}")
