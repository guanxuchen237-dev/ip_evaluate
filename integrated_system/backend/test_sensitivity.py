
import sys
import os
sys.path.append(os.getcwd())
from data_manager import DataManager

dm = DataManager()

# Case 1: The User's Current Input (from screenshot, looks like "Who dropped the prophecy?")
abstract_1 = "【伟大远征是弥天大谎！造就十二星神的‘金羊毛’...】" 

# Case 2: Clearly Garbage Text
abstract_bad = "asdf asdf testing garbage text nothing meaningful bad writing."

# Case 3: High Quality Text (Known Hit)
abstract_good = "这里是属于斗气的世界，没有花俏艳丽的魔法，有的，仅仅是繁衍到巅峰的斗气！" # Battle Through the Heavens intro

print("\n--- Sensitivity Test ---")
res1 = dm.predict_ip({'title': 'Test1', 'abstract': abstract_1, 'category': '玄幻', 'interaction': 0})
print(f"User Input Score: {res1['details']['content_potential_score']}")

res2 = dm.predict_ip({'title': 'Test2', 'abstract': abstract_bad, 'category': '玄幻', 'interaction': 0})
print(f"Garbage Text Score: {res2['details']['content_potential_score']}")

res3 = dm.predict_ip({'title': 'Test3', 'abstract': abstract_good, 'category': '玄幻', 'interaction': 0})
print(f"Masterpiece Score: {res3['details']['content_potential_score']}")
