import sys
sys.path.insert(0, r'd:\ip-lumina-main\integrated_system\backend')
import warnings
warnings.filterwarnings('ignore')
from data_manager import data_manager
print("Cols:", list(data_manager.df.columns))
coll_cols = [c for c in data_manager.df.columns if 'coll' in c.lower() or 'click' in c.lower() or 'fav' in c.lower() or 'sub' in c.lower()]
print("Related:", coll_cols)
if not data_manager.df.empty:
    r = data_manager.df.iloc[0]
    for c in coll_cols:
        print(f"  {c} = {r[c]}")
    print(f"  title = {r.get('title')}")
    print(f"  IP_Score = {r.get('IP_Score')}")
