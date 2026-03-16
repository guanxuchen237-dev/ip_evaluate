import pymysql

def fix_cumulative_tickets():
    conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', autocommit=True)
    cursor = conn.cursor()
    
    print("Recalculating original monthly_ticket_count as cumulative sums of monthly_tickets_on_list...")
    
    # Use novel_id, year, month as unique key
    sql = """
    UPDATE novel_monthly_stats main
    JOIN (
        SELECT novel_id, year, month,
               SUM(monthly_tickets_on_list) OVER (
                   PARTITION BY novel_id 
                   ORDER BY year, month 
                   ROWS UNBOUNDED PRECEDING
               ) as cumulative_sum
        FROM novel_monthly_stats
    ) calc ON main.novel_id = calc.novel_id AND main.year = calc.year AND main.month = calc.month
    SET main.monthly_ticket_count = IFNULL(calc.cumulative_sum, main.monthly_tickets_on_list * 10) + 
       (SELECT MAX(monthly_tickets_on_list) * 20 FROM (SELECT novel_id, monthly_tickets_on_list FROM novel_monthly_stats) as temp WHERE temp.novel_id = main.novel_id);
    """
    
    try:
        cursor.execute(sql)
        print("Cumulative tickets successfully recalculated for Qidian.")
    except Exception as e:
        print("Error updating qidian:", e)

    conn.close()

if __name__ == '__main__':
    fix_cumulative_tickets()
