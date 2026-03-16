import pandas as pd
import pymysql

def check_csv_vs_db():
    print("Reading CSV backup...")
    try:
        df_csv = pd.read_csv('integrated_system/backend/resources/data/cleaned_data.csv')
        print(f"Loaded {len(df_csv)} rows from cleaned_data.csv")
    except Exception as e:
        print("CSV load error:", e)
        return

    conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', charset='utf8mb4')
    
    # Compare Night's Nomenclature
    try:
        book_df = df_csv[df_csv['title'] == '夜的命名术'].sort_values(['year', 'month'], ascending=[False, False])
        print("=== CSV original data for 夜的命名术 ===")
        print(book_df[['title', 'year', 'month', 'monthly_tickets_on_list']].head())
        
        query = "SELECT year, month, rank_on_list, monthly_tickets_on_list, monthly_ticket_count FROM novel_monthly_stats WHERE title='夜的命名术' ORDER BY year DESC, month DESC LIMIT 5"
        db_df = pd.read_sql(query, conn)
        print("\n=== DB current data for 夜的命名术 ===")
        print(db_df.head())
    except Exception as e:
        print("Data check error:", e)

    conn.close()

if __name__ == '__main__':
    check_csv_vs_db()
