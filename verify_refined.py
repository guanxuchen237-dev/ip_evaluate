
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'integrated_system/backend'))
from data_manager import DataManager

def verify():
    dm = DataManager()
    books = [
        {'title': '齐天', 'category': '玄幻', 'word_count': 60000, 'finance': 6438, 'interaction': 150000, 'platform': 'Qidian', 'status': '连载'},
        {'title': '剑来', 'category': '仙侠', 'word_count': 11000000, 'finance': 2500, 'interaction': 5000000, 'platform': 'Zongheng', 'status': '连载'},
        {'title': '柯学验尸官', 'category': '都市', 'word_count': 3000000, 'finance': 25, 'interaction': 800000, 'platform': 'Qidian', 'status': '完结', 'updated_at': '2022-01-01'}
    ]
    
    for b in books:
        res = dm.predict_ip(b)
        print(f"[{b['title']}] Score: {res['score']}, Method: {res['method']}")
        print(f"   Trend: {res['details'].get('trend')}, Velocity: {res['details'].get('daily_velocity')}, Stability: {res['details'].get('stability')}")

if __name__ == "__main__":
    verify()
