from data_manager import DataManager

dm = DataManager()
dm.load_data()

print(f"Total Books in Memory: {len(dm.df)}")
library_data = dm.get_library_data(page=1, page_size=5)
print(f"Total Books in Library List (API): {library_data['total']}")

print("\nTop 5 in Library:")
for item in library_data['items']:
    print(f"Title: {item['title']}, Score: {item['ip_score']}, Platform: {item['platform']}")
