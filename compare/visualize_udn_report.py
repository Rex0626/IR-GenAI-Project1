import pandas as pd
import json
import os
import re
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager

# --- 設定中文字型 ---
# 確保圖表中的中文可以正常顯示
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # Windows 微軟正黑體
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"中文字型設定失敗，圖表標題可能顯示為亂碼: {e}")
    # 若在不同作業系統，可嘗試其他字型，例如 'Heiti TC' (macOS) 或 'Noto Sans CJK TC' (Linux)

def visualize_scraper_output(
    scraper_summary_path: str,
    scraper_diff_path: str,
    source_name: str,
    output_dir: str = "reports"
):
    """
    讀取由爬蟲程式自行產生的簡易比較結果 (summary.json, diff.csv)，
    並將這些結果轉換為視覺化圖表。
    """
    print(f"--- 正在為 {source_name} 的爬蟲現有結論進行視覺化 ---")
    os.makedirs(output_dir, exist_ok=True)

    # --- 圖表 1: 資料變動摘要長條圖 (來自 summary.json) ---
    try:
        with open(scraper_summary_path, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        counts = {
            '新增 (Added)': summary_data.get('added', 0),
            '刪除 (Removed)': summary_data.get('removed', 0),
            '修改 (Changed)': summary_data.get('changed', 0)
        }
        df_counts = pd.DataFrame(list(counts.items()), columns=['變動類型', '數量'])

        plt.figure(figsize=(8, 6))
        sns.barplot(data=df_counts, x='變動類型', y='數量', palette="mako")
        plt.title(f'{source_name} - 資料變動摘要 (來自爬蟲報告)', fontsize=16)
        plt.xlabel('變動類型', fontsize=12)
        plt.ylabel('資料筆數', fontsize=12)
        plt.tight_layout()

        chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_summary.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存摘要圖表 -> {chart_path}")

    except Exception as e:
        print(f"產生圖表 1 (摘要) 失敗: {e}")

    # --- 圖表 2: 新增/刪除項目之分類分佈圖 (來自 diff.csv) ---
    try:
        df_diff = pd.read_csv(scraper_diff_path)
        
        def guess_category_from_url(url: str) -> str:
            match = re.search(r"/news/story/(\d+)/", str(url))
            return match.group(1) if match else "未知分類"
            
        df_diff['category'] = df_diff['url'].apply(guess_category_from_url)
        
        df_plot = df_diff[df_diff['status'].isin(['ADDED', 'REMOVED'])]
        
        if not df_plot.empty:
            plt.figure(figsize=(12, 8))
            sns.countplot(data=df_plot, y='category', hue='status', palette={'ADDED': 'green', 'REMOVED': 'red'})
            
            plt.title(f'{source_name} - 新增/刪除項目之分類分佈', fontsize=16)
            plt.xlabel('項目數量', fontsize=12)
            plt.ylabel('分類 ID', fontsize=12)
            plt.legend(title='狀態')
            plt.tight_layout()

            chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_category_changes_from_scraper.png")
            plt.savefig(chart_path)
            plt.close()
            print(f"已儲存分類變動圖表 -> {chart_path}")
        else:
            print("diff.csv 中無新增或刪除的資料可供繪製分類圖。")

    except Exception as e:
        print(f"產生圖表 2 (分類變動) 失敗: {e}")


# ==============================================================================
# 主程式執行區塊
# ==============================================================================
if __name__ == '__main__':
    
    # --- 【重要】請將路徑指向由「UDN 爬蟲」產生的報告檔案 ---
    # 這些路徑需要根據您 UDN 爬蟲的實際輸出位置來修改！
    # 假設 UDN 爬蟲會把它自己的報告輸出到 `reports` 資料夾中。
    
    # 第二次執行爬蟲後產生的報告路徑
    summary_path = 'reports/summary.json'
    diff_path = 'reports/diff_20251015.csv' # 請確認日期和檔名

    if os.path.exists(summary_path) and os.path.exists(diff_path):
        visualize_scraper_output(
            scraper_summary_path=summary_path,
            scraper_diff_path=diff_path,
            source_name='udn_sports'
        )
    else:
        print(f"找不到 UDN 爬蟲產生的報告檔案，請確認路徑是否正確。")
        print(f"預期檔案: {summary_path}, {diff_path}")