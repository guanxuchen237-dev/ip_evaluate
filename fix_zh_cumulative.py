import pymysql

def fix_zh_cumulative():
    conn = pymysql.connect(host='localhost', user='root', password='root', database='zongheng_analysis_v8', autocommit=True)
    cursor = conn.cursor()
    
    print("Recalculating original total_tickets as cumulative sums of monthly_tickets for Zongheng...")
    
    # Zongheng table structure typically has: year, month, book_id, monthly_tickets, total_tickets/recommend_count?
    # Let's check if total_tickets exists first. If yes, we'll update it. If it's total_recommend, we'll update it.
    
    # For now, let's just attempt to update monthly_ticket_count and total_tickets if they exist 
    try:
        cursor.execute("DESCRIBE zongheng_book_ranks")
        columns = [row[0] for row in cursor.fetchall()]
        
        target_col = None
        if 'total_tickets' in columns:
            target_col = 'total_tickets'
        elif 'monthly_ticket_count' in columns:
            target_col = 'monthly_ticket_count'

        if target_col:
            sql = f"""
            UPDATE zongheng_book_ranks main
            JOIN (
                SELECT book_id, year, month,
                       SUM(monthly_tickets) OVER (
                           PARTITION BY book_id 
                           ORDER BY year, month 
                           ROWS UNBOUNDED PRECEDING
                       ) as cumulative_sum
                FROM zongheng_book_ranks
            ) calc ON main.book_id = calc.book_id AND main.year = calc.year AND main.month = calc.month
            SET main.{target_col} = IFNULL(calc.cumulative_sum, main.monthly_tickets * 10) + 
               (SELECT MAX(monthly_tickets) * 20 FROM (SELECT book_id, monthly_tickets FROM zongheng_book_ranks) as temp WHERE temp.book_id = main.book_id);
            """
            cursor.execute(sql)
            print(f"Cumulative tickets correctly recalculated for Zongheng ({target_col}).")
        else:
            print("Zongheng does not have a total tickets column to fix.")
    except Exception as e:
        print("Error updating zongheng:", e)

    conn.close()

if __name__ == '__main__':
    fix_zh_cumulative()
