import pandas as pd

def read_csv_columns():
    df = pd.read_csv('integrated_system/backend/resources/data/cleaned_data.csv')
    print("CSV Columns:", df.columns.tolist())
    if 'monthly_tickets' in df.columns:
        print(df[['title', 'monthly_tickets', 'year', 'month']].head())
    
if __name__ == '__main__':
    read_csv_columns()
