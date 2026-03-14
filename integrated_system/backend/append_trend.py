import os

filepath = 'd:/ip-lumina-main/integrated_system/backend/data_manager.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

func_code = '''
    def get_long_term_trend(self, platform='qidian'):
        """Long Term Interaction/Finance Trend for specific hot titles"""
        if self.df.empty: return {'dates': [], 'series': []}
        try:
            if platform == 'qidian':
                titles = ['诡秘之主', '轮回乐园', '神话版三国', '大奉打更人', '赤心巡天']
            else:
                titles = ['逆天邪神', '剑来', '剑道第一仙', '日月风华', '不让江山']
                
            df_filtered = self.df[self.df['title'].isin(titles)].copy()
            if df_filtered.empty: return {'dates': [], 'series': []}
            
            df_filtered = df_filtered.dropna(subset=['year', 'month'])
            df_filtered['date'] = df_filtered['year'].astype(int).astype(str) + '-' + df_filtered['month'].astype(int).astype(str).str.zfill(2)
            grouped = df_filtered.groupby(['title', 'date'])['finance'].max().reset_index()
            dates = sorted(grouped['date'].unique().tolist())
            
            series_data = []
            for title in titles:
                book_data = grouped[grouped['title'] == title]
                date_val_map = dict(zip(book_data['date'], book_data['finance']))
                values = [int(date_val_map.get(d, 0)) for d in dates]
                series_data.append({'name': title, 'data': values})
                
            return {'dates': dates, 'series': series_data}
        except Exception as e:
            print(f"Long Term Trend Error: {e}")
            return {'dates': [], 'series': []}

data_manager = DataManager()
'''

if 'def get_long_term_trend' not in content:
    content = content.replace('data_manager = DataManager()', func_code)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        print("Updated data_manager.py")
else:
    print("Already updated data_manager.py")
