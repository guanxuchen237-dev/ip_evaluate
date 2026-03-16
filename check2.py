import sys; sys.path.insert(0, 'd:/ip-lumina-main/integrated_system/backend')
from data_manager import data_manager

books = ['赤心巡天', '这个魔神明明很强却过分多疑', '无敌天命', '玄鉴仙族', '剑来']
for b in books:
    row = data_manager.df[data_manager.df['title'].str.contains(b, na=False)]
    if not row.empty:
        print(f"{b}: DB_Score={row['IP_Score'].values[0]}, finance={row['finance'].values[0]}, inter={row['interaction'].values[0]}, pop={row['popularity'].values[0]}")
    else:
        print(f"{b}: NOT FOUND IN DB")
