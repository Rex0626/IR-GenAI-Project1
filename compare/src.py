import pandas as pd
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager

# 指定中文字型（以 Windows 為例）
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 微軟正黑體
plt.rcParams['axes.unicode_minus'] = False  # 正常顯示負號

# ==============================================================================
# 函式 1: 專門進行資料比較與報告生成
# ==============================================================================
def generate_diff_report(
    old_file_path: str,
    new_file_path: str,
    source_name: str,
    key_columns: list = ['price/value', 'title', 'category'],
    output_dir: str = "reports"
):
    """
    比較兩個版本的爬蟲資料，並產生差異報告 (JSON 和 CSV)。
    """
    # --- 1. 載入與預處理資料 ---
    try:
        df_old = pd.read_csv(old_file_path)
        df_new = pd.read_csv(new_file_path)
        print(f"成功載入資料: 舊資料 {len(df_old)} 筆, 新資料 {len(df_new)} 筆。")
    except FileNotFoundError as e:
        print(f"錯誤：找不到檔案 {e}")
        return None, None

    df_old['id'] = df_old['id'].astype(str)
    df_new['id'] = df_new['id'].astype(str)

    # --- 2. 進行比較 ---
    old_ids = set(df_old['id'])
    new_ids = set(df_new['id'])

    # 新增 (Added)
    added_ids = new_ids - old_ids
    df_added = df_new[df_new['id'].isin(added_ids)].copy()
    df_added['status'] = 'added'

    # 刪除 (Deleted)
    deleted_ids = old_ids - new_ids
    df_deleted = df_old[df_old['id'].isin(deleted_ids)].copy()
    df_deleted['status'] = 'deleted'

    # 修改 (Modified)
    common_ids = old_ids.intersection(new_ids)
    df_old_common = df_old[df_old['id'].isin(common_ids)].set_index('id').sort_index()
    df_new_common = df_new[df_new['id'].isin(common_ids)].set_index('id').sort_index()
    
    # 確保比較的欄位都存在
    valid_key_columns = [col for col in key_columns if col in df_old_common.columns and col in df_new_common.columns]
    
    modified_ids = []
    if valid_key_columns:
        comparison_df = (df_old_common[valid_key_columns] != df_new_common[valid_key_columns])
        modified_mask = comparison_df.any(axis=1)
        modified_ids = df_old_common[modified_mask].index.tolist()

    df_modified_diff = pd.DataFrame()
    if modified_ids:
        df_modified_old = df_old[df_old['id'].isin(modified_ids)]
        df_modified_new = df_new[df_new['id'].isin(modified_ids)]
        df_modified_diff = pd.merge(df_modified_old, df_modified_new, on='id', suffixes=('_old', '_new'))
        df_modified_diff['status'] = 'modified'

    print(f"比較結果: {len(df_added)} 筆新增, {len(df_deleted)} 筆刪除, {len(modified_ids)} 筆修改。")
    
    # --- 3. 產生報告檔案 ---
    os.makedirs(output_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")

    summary_data = {
        "source": source_name,
        "run_timestamp": datetime.now().isoformat(),
        "files": {"old": os.path.basename(old_file_path), "new": os.path.basename(new_file_path)},
        "counts": {"added": len(df_added), "deleted": len(df_deleted), "modified": len(modified_ids)}
    }
    summary_path = os.path.join(output_dir, f"summary_{source_name}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=4, ensure_ascii=False)
    print(f"已儲存摘要報告 -> {summary_path}")

    df_diff_report = pd.concat([df_added, df_deleted, df_modified_diff], ignore_index=True)
    diff_path = os.path.join(output_dir, f"diff_{source_name}_{today_str}.csv")
    df_diff_report.to_csv(diff_path, index=False)
    print(f"已儲存詳細差異報告 -> {diff_path}")

    return summary_data, df_diff_report

# ==============================================================================
# 函式 2: 專門進行資料視覺化
# ==============================================================================
def create_visualizations(
    dataframe: pd.DataFrame,
    source_name: str,
    output_dir: str = "reports"
):
    """
    根據提供的 DataFrame 產生並儲存 3 張視覺化圖表。
    """
    if dataframe.empty:
        print("資料為空，無法產生圖表。")
        return

    print(f"--- 正在為 {source_name} 產生視覺化圖表 ---")
    os.makedirs(output_dir, exist_ok=True)
    
    # --- 圖表 1: 分類數量長條圖 (Top 15) ---
    try:
        plt.figure(figsize=(12, 8))
        category_counts = dataframe['category'].value_counts().nlargest(15)
        sns.barplot(x=category_counts.values, y=category_counts.index, palette="viridis")
        plt.title(f'{source_name} - 分類數量分佈 (Top 15)', fontsize=16)
        plt.xlabel('數量', fontsize=12)
        plt.ylabel('分類', fontsize=12)
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"chart_{source_name}_categories.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存圖表 1 -> {chart_path}")
    except Exception as e:
        print(f"產生圖表 1 (分類) 失敗: {e}")

    # --- 圖表 2: 價格/數值分佈直方圖 ---
    try:
        plt.figure(figsize=(10, 6))
        sns.histplot(dataframe['price/value'], bins=30, kde=True, color="skyblue")
        plt.title(f'{source_name} - 數值分佈 (price/value)', fontsize=16)
        plt.xlabel('價格 / 數值', fontsize=12)
        plt.ylabel('頻率', fontsize=12)
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"chart_{source_name}_price_distribution.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存圖表 2 -> {chart_path}")
    except Exception as e:
        print(f"產生圖表 2 (數值分佈) 失敗: {e}")

# ==============================================================================
# 函式 3: 專門進行「比較結果」的視覺化 (【最終版】，保證產生所有圖表)
# ==============================================================================
def create_comparison_visualizations(
    summary_data: dict,
    diff_dataframe: pd.DataFrame,
    source_name: str,
    output_dir: str = "reports"
):
    """
    根據差異分析的結果，產生並儲存 3 張專門的「比較」視覺化圖表。
    此版本確保在沒有修改資料時，也會產生帶有提示的空白圖表，以維持報告一致性。
    """
    if not summary_data:
        print("沒有摘要資料，跳過差異視覺化。")
        return

    print(f"--- 正在為 {source_name} 產生「比較結果」視覺化圖表 ---")
    os.makedirs(output_dir, exist_ok=True)

    # --- 圖表 1: 資料變動摘要長條圖 (此圖表一定會產生) ---
    try:
        counts = summary_data.get('counts', {})
        df_counts = pd.DataFrame(list(counts.items()), columns=['變動類型', '數量'])
        
        status_map = {'added': '新增 (Added)', 'deleted': '刪除 (Deleted)', 'modified': '修改 (Modified)'}
        df_counts['變動類型'] = df_counts['變動類型'].map(status_map)

        plt.figure(figsize=(8, 6))
        sns.barplot(data=df_counts, x='變動類型', y='數量', palette="mako")
        plt.title(f'{source_name} - 資料變動摘要', fontsize=16)
        plt.xlabel('變動類型', fontsize=12)
        plt.ylabel('資料筆數', fontsize=12)
        plt.tight_layout()

        chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_summary.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存比較圖表 1 -> {chart_path}")
    except Exception as e:
        print(f"產生比較圖表 1 (摘要) 失敗: {e}")

    # 篩選出被修改的資料
    df_modified = diff_dataframe[diff_dataframe['status'] == 'modified'].copy() if diff_dataframe is not None else pd.DataFrame()

    # --- 圖表 2: 修改項目之價格變動散佈圖 ---
    try:
        plt.figure(figsize=(8, 8))
        # 【修改邏輯】如果 df_modified 不是空的，且有價格欄位，就畫圖
        if not df_modified.empty and 'price/value_old' in df_modified.columns and 'price/value_new' in df_modified.columns and not df_modified.dropna(subset=['price/value_old', 'price/value_new']).empty:
            df_plot = df_modified.dropna(subset=['price/value_old', 'price/value_new'])
            sns.scatterplot(data=df_plot, x='price/value_old', y='price/value_new', alpha=0.7)
            max_val = max(df_plot['price/value_old'].max(), df_plot['price/value_new'].max())
            plt.plot([0, max_val], [0, max_val], 'r--', label='價格不變')
            plt.legend()
        # 【新增邏輯】如果沒有修改資料，就顯示一張空白的圖表與提示文字
        else:
            plt.text(0.5, 0.5, '本次更新中無價格變動的資料', ha='center', va='center', fontsize=14, color='gray')
            plt.gca().get_xaxis().set_visible(False)
            plt.gca().get_yaxis().set_visible(False)
            
        plt.title(f'{source_name} - 修改項目之價格變動', fontsize=16)
        plt.xlabel('修改前的價格 (Old Price)', fontsize=12)
        plt.ylabel('修改後的價格 (New Price)', fontsize=12)
        plt.grid(True)
        plt.axis('equal')
        plt.tight_layout()
        
        chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_price_change.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存比較圖表 2 -> {chart_path}")
    except Exception as e:
        print(f"產生比較圖表 2 (價格變動) 失敗: {e}")

    # --- 圖表 3: 修改最頻繁的分類長條圖 (Top 10) ---
    try:
        plt.figure(figsize=(10, 7))
        # 【修改邏輯】如果 df_modified 不是空的，且有分類欄位，就畫圖
        if not df_modified.empty and 'category_old' in df_modified.columns and not df_modified['category_old'].dropna().empty:
            modified_category_counts = df_modified['category_old'].value_counts().nlargest(10)
            sns.barplot(x=modified_category_counts.values, y=modified_category_counts.index, palette="rocket")
        # 【新增邏輯】如果沒有修改資料，就顯示空白圖表與提示
        else:
            plt.text(0.5, 0.5, '本次更新中無分類被修改的資料', ha='center', va='center', fontsize=14, color='gray')
            plt.gca().get_xaxis().set_visible(False)
            plt.gca().get_yaxis().set_visible(False)

        plt.title(f'{source_name} - 修改最頻繁的分類 (Top 10)', fontsize=16)
        plt.xlabel('修改次數', fontsize=12)
        plt.ylabel('分類 (修改前)', fontsize=12)
        plt.tight_layout()
        
        chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_modified_categories.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存比較圖表 3 -> {chart_path}")
    except Exception as e:
        print(f"產生比較圖表 3 (分類修改) 失敗: {e}")

# ==============================================================================
# 主程式執行區塊
# ==============================================================================
if __name__ == '__main__':
    # --- 設定檔案路徑 (請根據您的實際情況修改這裡) ---
    static_old_file = 'data/books_static_20251011_p5.csv'
    static_new_file = 'data/books_static_20251011_p8.csv'

    dynamic_old_file = 'data/quotes_dynamic_20251011_p5.csv'
    dynamic_new_file = 'data/quotes_dynamic_20251011_p8.csv'

    # --- 處理靜態資料 ---
    print("--- 正在處理靜態 (Static) 資料 ---")
    if os.path.exists(static_old_file) and os.path.exists(static_new_file):
        # 步驟 1: 執行比較，並用變數接收回傳的 摘要(summary) 和 差異報告(diff)
        static_summary, static_diff = generate_diff_report(
            old_file_path=static_old_file,
            new_file_path=static_new_file,
            source_name='books_static'
        )
        
        # 步驟 2: 根據最新資料進行「狀態」分析視覺化
        df_static_new = pd.read_csv(static_new_file)
        create_visualizations(
            dataframe=df_static_new,
            source_name='books_static'
        )

        # 步驟 3: 將步驟 1 的比較結果傳入，進行「差異」分析視覺化
        if static_summary and static_diff is not None:
            create_comparison_visualizations(
                summary_data=static_summary,
                diff_dataframe=static_diff,
                source_name='books_static'
            )
    else:
        print(f"找不到靜態資料檔案，跳過處理。")

    print("\n" + "="*50 + "\n")

    # --- 處理動態資料 ---
    print("--- 正在處理動態 (Dynamic) 資料 ---")
    if os.path.exists(dynamic_old_file) and os.path.exists(dynamic_new_file):
        # 同樣地，接收比較結果
        dynamic_summary, dynamic_diff = generate_diff_report(
            old_file_path=dynamic_old_file,
            new_file_path=dynamic_new_file,
            source_name='quotes_dynamic',
            key_columns=['title', 'author/vendor', 'category']
        )
        
        # 進行「狀態」分析視覺化
        df_dynamic_new = pd.read_csv(dynamic_new_file)
        create_visualizations(
            dataframe=df_dynamic_new,
            source_name='quotes_dynamic'
        )

        # 進行「差異」分析視覺化
        if dynamic_summary and dynamic_diff is not None:
            create_comparison_visualizations(
                summary_data=dynamic_summary,
                diff_dataframe=dynamic_diff,
                source_name='quotes_dynamic'
            )
    else:
        print(f"找不到動態資料檔案，跳過處理。")