import pandas as pd
import os
from compare.src import generate_diff_report

# 準備測試用的假資料
df_old_data = pd.DataFrame({
    'id': ['a1', 'a2', 'a3'],
    'title': ['Book A', 'Book B', 'Book C'],
    'price/value': [10.0, 20.0, 30.0],
    'category': ['Sci-Fi', 'Art', 'Music']
})

# 測試 1: 驗證「新增」一筆資料
def test_added_item():
    df_new_data = pd.DataFrame({
        'id': ['a1', 'a2', 'a3', 'a4'], # 新增 a4
        'title': ['Book A', 'Book B', 'Book C', 'Book D'],
        'price/value': [10.0, 20.0, 30.0, 40.0],
        'category': ['Sci-Fi', 'Art', 'Music', 'Sci-Fi']
    })
    
    # 將假資料存成暫存檔
    df_old_data.to_csv("test_old.csv", index=False)
    df_new_data.to_csv("test_new.csv", index=False)

    summary, diff = generate_diff_report("test_old.csv", "test_new.csv", "test")
    
    # 斷言 (Assert): 檢查新增數量是否為 1
    assert summary['counts']['added'] == 1
    assert summary['counts']['deleted'] == 0
    assert summary['counts']['modified'] == 0
    
    # 清理暫存檔
    os.remove("test_old.csv")
    os.remove("test_new.csv")

# 測試 2: 驗證「刪除」一筆資料
def test_deleted_item():
    df_new_data = pd.DataFrame({
        'id': ['a1', 'a3'], # 刪除 a2
        'title': ['Book A', 'Book C'],
        'price/value': [10.0, 30.0],
        'category': ['Sci-Fi', 'Music']
    })
    
    df_old_data.to_csv("test_old.csv", index=False)
    df_new_data.to_csv("test_new.csv", index=False)
    summary, diff = generate_diff_report("test_old.csv", "test_new.csv", "test")
    
    # 斷言: 檢查刪除數量是否為 1
    assert summary['counts']['deleted'] == 1
    assert summary['counts']['added'] == 0
    
    os.remove("test_old.csv")
    os.remove("test_new.csv")

# 測試 3: 驗證「修改」一筆資料
def test_modified_item():
    df_new_data = pd.DataFrame({
        'id': ['a1', 'a2', 'a3'],
        'title': ['Book A', 'Book B', 'Book C New Name'], # 修改 a3 的 title
        'price/value': [10.0, 25.5, 30.0], # 修改 a2 的 price
        'category': ['Sci-Fi', 'Art', 'Music']
    })
    
    df_old_data.to_csv("test_old.csv", index=False)
    df_new_data.to_csv("test_new.csv", index=False)
    summary, diff = generate_diff_report("test_old.csv", "test_new.csv", "test")
    
    # 斷言: 檢查修改數量是否為 2
    assert summary['counts']['modified'] == 2
    assert summary['counts']['added'] == 0
    
    os.remove("test_old.csv")
    os.remove("test_new.csv")
    
# 測試 4: 驗證資料完全「沒有變動」
def test_no_change():
    # 新舊資料完全一樣
    df_new_data = df_old_data.copy()
    
    df_old_data.to_csv("test_old.csv", index=False)
    df_new_data.to_csv("test_new.csv", index=False)
    summary, diff = generate_diff_report("test_old.csv", "test_new.csv", "test")
    
    # 斷言: 檢查所有變動數量是否皆為 0
    assert summary['counts']['added'] == 0
    assert summary['counts']['deleted'] == 0
    assert summary['counts']['modified'] == 0
    
    os.remove("test_old.csv")
    os.remove("test_new.csv")