import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'integrated_system/backend'))
from data_manager import data_manager

df2024_2 = data_manager.df[(data_manager.df['year'] == 2024) & (data_manager.df['month'] == 2)]
print("Count for 2024-02:", len(df2024_2))

print("Value counts by year:\n", data_manager.df['year'].value_counts())
