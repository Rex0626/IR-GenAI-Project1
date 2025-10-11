# 專案名稱：雙來源網頁爬蟲與增量更新及差異摘要

## 專案描述
本專案為「資訊檢索與生成式人工智慧」課程之期中專案。系統會從一個靜態網站 (Books to Scrape) 和一個動態網站 (Quotes to Scrape) 爬取資料，支援增量更新，並能自動生成差異比較報告與視覺化圖表。

## 環境設定
1.  **安裝 Anaconda**: 請先安裝 Anaconda 環境。
2.  **建立虛擬環境**:
    ```bash
    conda create --name ir_project python=3.9
    ```
3.  **啟用虛擬環境**:
    ```bash
    conda activate ir_project
    ```
4.  **安裝依賴套件**: (注意：檔名是 requirement.txt)
    ```bash
    pip install -r requirement.txt
    playwright install
    ```

## 如何執行
專案提供了 `run_first_time.sh` 和 `run_incremental.sh` 腳本，方便執行。

1.  **首次完整爬取**:
    執行此腳本會爬取少量資料作為初始版本。
    ```bash
    bash run_first_time.sh
    ```
2.  **增量更新爬取**:
    執行此腳本會爬取更多頁面的資料，以模擬資料更新。
    ```bash
    bash run_incremental.sh
    ```
3.  **執行差異分析**:
    爬取完兩次資料後，請確認 `compare/src.py` 中的檔案路徑設定正確，然後執行：
    ```bash
    python compare/src.py
    ```
4.  **啟動互動介面**:
    ```bash
    streamlit run app.py
    ```
5.  **執行單元測試**:
    ```bash
    pytest
    ```

## 專案結構
- `/compare`: 存放資料比較與分析相關的程式碼。
  - `src.py`: 執行差異分析與視覺化的主要腳本。
  - `__init__.py`: 將此資料夾標記為 Python 套件。
- `/dual_source_scraper`: 存放爬蟲相關的程式碼與產出。
  - `/data`: 存放爬蟲抓取的 CSV 檔案。
  - `/logs`: 存放錯誤日誌。
  - `/src`: 存放靜態與動態爬蟲的 Python 腳本。
- `app.py`: Streamlit 互動介面腳本。
- `test_analysis.py`: Pytest 單元測試腳本。
- `README.md`: 本說明檔案。
- `requirement.txt`: 專案依賴套件列表。
- `run_first_time.sh`: 首次執行爬蟲的腳本。
- `run_incremental.sh`: 增量更新爬蟲的腳本。