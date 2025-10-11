import streamlit as st
import pandas as pd
import os

# --- 網頁設定 ---
st.set_page_config(page_title="期中專案成果", layout="wide")
st.title("雙來源網頁爬蟲與差異分析 成果展示")

# --- 載入資料與圖表 ---
# 讓使用者可以選擇要看哪個來源的資料
source_choice = st.selectbox("請選擇要查看的資料來源：", ["靜態網站 (books_static)", "動態網站 (quotes_dynamic)"])

if "static" in source_choice:
    source_name = "books_static"
    # 【路徑修正 1】data_file 的路徑也需要對應您的專案結構
    data_file = os.path.join('dual_source_scraper', 'data', 'books_static_20251011_p8.csv') # 【請確認檔名正確】
else:
    source_name = "quotes_dynamic"
    # 【路徑修正 2】data_file 的路徑也需要對應您的專案結構
    data_file = os.path.join('dual_source_scraper', 'data', 'quotes_dynamic_20251011_p8.csv') # 【請確認檔名正確】

# 【路徑修正 3 - 核心修正】顯示比較摘要圖
summary_chart_path = os.path.join("compare", "reports", f"chart_comp_{source_name}_summary.png")

if os.path.exists(summary_chart_path):
    st.header("資料變動摘要")
    st.image(summary_chart_path, caption="顯示新增、刪除與修改的資料筆數。")
else:
    st.warning(f"找不到摘要圖表：{summary_chart_path}")

# 顯示資料表格與關鍵字搜尋
st.header("資料檢視與搜尋")
if os.path.exists(data_file):
    df = pd.read_csv(data_file)

    # 建立一個簡單的關鍵字搜尋框
    keyword = st.text_input("輸入關鍵字搜尋標題 (Title):")
    if keyword:
        # 根據關鍵字篩選 DataFrame (不分大小寫)
        result_df = df[df['title'].str.contains(keyword, case=False, na=False)]
        st.dataframe(result_df)
    else:
        # 沒有關鍵字時，顯示完整資料
        st.dataframe(df)
else:
    st.error(f"找不到資料檔案：{data_file}")