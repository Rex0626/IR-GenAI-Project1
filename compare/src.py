import pandas as pd
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import platform
from matplotlib import font_manager

# ==========================================================
# 🛠 使用者設定區（請根據實際路徑修改）
# ==========================================================
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR   = os.path.join(BASE_DIR, 'data')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')

# 【靜態資料】
static_old_file= os.path.join(DATA_DIR, 'books_static_20251011_p5.csv')
static_new_file= os.path.join(DATA_DIR, 'books_static_20251011_p8.csv')

# 【動態資料】
dynamic_old_file = os.path.join(DATA_DIR, 'quotes_dynamic_20251011_p5.csv')
dynamic_new_file = os.path.join(DATA_DIR, 'quotes_dynamic_20251011_p10.csv')
# ==========================================================

# 指定中文字型（以 Windows 為例）
# 自動偵測作業系統，設定中文顯示字型
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'PingFang TC', 'Arial Unicode MS']
elif platform.system() == 'Windows':
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
else:  # Linux 或其他
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'SimHei']

plt.rcParams['axes.unicode_minus'] = False  # 正常顯示負號
# ==============================================================================
# 函式 1: 專門進行資料比較與報告生成
# ==============================================================================
SOURCES = {
    "books_static": {
        "old_file": static_old_file,  
        "new_file": static_new_file,  
        "key_columns": ['price/value', 'title', 'category'],
        "visual_focus": "price",
    },
    "quotes_dynamic": {
        "old_file": dynamic_old_file, 
        "new_file": dynamic_new_file, 
        "key_columns": ['title', 'author/vendor', 'category'],
        "visual_focus": "author",
    }
}

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

    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # ✅【唯一定點修改】quotes_dynamic 的比對欄位與前處理（其它程式碼完全不動）
    if source_name == 'quotes_dynamic':
        # 只用引言內容判定是否修改（若你要把作者/分類也納入，改成 ['title','author/vendor','category']）
        key_columns = ['title','author/vendor']

        # title 輕量清洗：統一引號、去除前後空白
        if 'title' in df_old_common.columns:
            df_old_common['title'] = df_old_common['title'].apply(
                lambda x: x.replace('“','"').replace('”','"').replace('’',"'").strip()
                if isinstance(x, str) else x
            )
        if 'title' in df_new_common.columns:
            df_new_common['title'] = df_new_common['title'].apply(
                lambda x: x.replace('“','"').replace('”','"').replace('’',"'").strip()
                if isinstance(x, str) else x
            )

        # category 正規化：全/半形空白、大小寫、分隔符（| , / ;）→ 轉為排序去重後的集合字串
        import re
        def _norm_cat(s):
            if not isinstance(s, str): return s
            s = s.replace('　', ' ').strip().lower()
            parts = [p.strip() for p in re.split(r'[|,/;]', s) if p.strip()]
            return '|'.join(sorted(set(parts)))
        if 'category' in df_old_common.columns:
            df_old_common['category'] = df_old_common['category'].apply(_norm_cat)
        if 'category' in df_new_common.columns:
            df_new_common['category'] = df_new_common['category'].apply(_norm_cat)
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # 確保比較的欄位都存在
    valid_key_columns = [col for col in key_columns if col in df_old_common.columns and col in df_new_common.columns]
    
    modified_ids = []
    if valid_key_columns:
        comparison_df = (df_old_common[valid_key_columns] != df_new_common[valid_key_columns])
        modified_mask = comparison_df.any(axis=1)
        modified_ids = df_old_common[modified_mask].index.tolist()
    print("✅ added_ids:", added_ids)
    print("✅ deleted_ids:", deleted_ids)
    print("✅ modified_ids:", modified_ids)
    print("✅ valid_key_columns:", valid_key_columns)
    if modified_ids:
        print("🔍 偵測到修改的項目：")
        for mid in modified_ids:
            diffs = comparison_df.loc[mid]
            changed_cols = [c for c, changed in diffs.items() if changed]
            print(f" - id={mid}, 改變欄位={changed_cols}")
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
    if not summary_data:
        print("沒有摘要資料，跳過差異視覺化。")
        return

    print(f"--- 正在為 {source_name} 產生「比較結果」視覺化圖表 ---")
    os.makedirs(output_dir, exist_ok=True)

    # 若為 quotes_dynamic，只產生 summary 圖
    if "quotes_dynamic" in source_name:
        try:
            counts = summary_data.get('counts', {})
            df_counts = pd.DataFrame(list(counts.items()), columns=['變動類型', '數量'])
            df_counts['變動類型'] = df_counts['變動類型'].map({'added': '新增', 'deleted': '刪除', 'modified': '修改'})

            plt.figure(figsize=(8, 6))
            sns.barplot(data=df_counts, x='變動類型', y='數量', palette="mako")
            plt.title(f'{source_name} - 資料變動摘要', fontsize=16)
            plt.tight_layout()

            chart_path = os.path.join(output_dir, f"chart_comp_{source_name}_summary.png")
            plt.savefig(chart_path)
            plt.close()
            print(f"已儲存比較圖表 (僅摘要) -> {chart_path}")
        except Exception as e:
            print(f"產生比較圖表 (摘要) 失敗: {e}")
        return  # 🟡 結束函式，不畫價格與分類圖

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

def create_visualizations_quotes(dataframe, source_name, output_dir="reports"):
    """
    為引言類型資料產生視覺化圖表。
    例如：作者出現次數、主題分佈。
    """
    if dataframe.empty:
        print("資料為空，無法產生圖表。")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 1️⃣ 作者出現次數 Top 15
    try:
        plt.figure(figsize=(12, 8))
        author_counts = dataframe['author/vendor'].value_counts().nlargest(15)
        sns.barplot(x=author_counts.values, y=author_counts.index, palette="crest")
        plt.title(f'{source_name} - 作者出現次數 (Top 15)', fontsize=16)
        plt.xlabel('數量', fontsize=12)
        plt.ylabel('作者 / 出處', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"chart_{source_name}_authors.png"))
        plt.close()
    except Exception as e:
        print(f"產生圖表 1 (作者統計) 失敗: {e}")

    # 2️⃣ 主題分類分佈 (Top 10)
    try:
        plt.figure(figsize=(10, 6))
        cat_counts = dataframe['category'].value_counts().nlargest(10)
        sns.barplot(x=cat_counts.values, y=cat_counts.index, palette="flare")
        plt.title(f'{source_name} - 主題分類分佈', fontsize=16)
        plt.xlabel('數量', fontsize=12)
        plt.ylabel('主題分類', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"chart_{source_name}_categories.png"))
        plt.close()
    except Exception as e:
        print(f"產生圖表 2 (主題分類) 失敗: {e}")
        
        # 🆕 3️⃣ 作者數量分佈（完整長條圖）
    try:
        plt.figure(figsize=(14, 8))
        author_counts_all = dataframe['author'].value_counts()
        sns.barplot(x=author_counts_all.values, y=author_counts_all.index, palette="ch:s=.25,rot=-.25")
        plt.title(f'{source_name} - 作者數量分佈（完整）', fontsize=16)
        plt.xlabel('引言數量', fontsize=12)
        plt.ylabel('作者', fontsize=12)
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"chart_{source_name}_authors_full.png")
        plt.savefig(chart_path)
        plt.close()
        print(f"已儲存圖表 3 (作者完整分佈) -> {chart_path}")
    except Exception as e:
        print(f"產生圖表 3 (作者完整分佈) 失敗: {e}")
# ==============================================================================
# 主程式執行區塊
# ==============================================================================
if __name__ == '__main__':
    for source_name, config in SOURCES.items():
        print(f"--- 處理來源：{source_name} ---")

        old_file = config["old_file"]
        new_file = config["new_file"]

        if os.path.exists(old_file) and os.path.exists(new_file):
            summary, diff = generate_diff_report(
                old_file_path=old_file,
                new_file_path=new_file,
                source_name=source_name,
                key_columns=config["key_columns"],
                output_dir=REPORT_DIR   # <- 用統一的輸出資料夾
            )

            df_new = pd.read_csv(new_file)

            # 依來源選擇視覺化
            if config["visual_focus"] == "price":
                create_visualizations(df_new, source_name, output_dir=REPORT_DIR)
            elif config["visual_focus"] == "author":
                create_visualizations_quotes(df_new, source_name, output_dir=REPORT_DIR)

            # 差異圖表（內部已處理無價格欄位時的顯示/略過）
            create_comparison_visualizations(
                summary_data=summary,
                diff_dataframe=diff,
                source_name=source_name,
                output_dir=REPORT_DIR
            )
        else:
            print(f"⚠️ 找不到資料檔案，略過 {source_name}")