#!/bin/bash
echo "--- 首次執行爬蟲 ---"

# 執行靜態爬蟲，爬取 5 頁
python dual_source_scraper/src/scrape_static.py --pages 5

# 執行動態爬蟲，爬取 5 頁
python dual_source_scraper/src/scrape_dynamic.py --pages 5

# 執行新的動態爬蟲，爬取 100 筆
python dual_source_scraper/src/scrape_new_dynamic.py --limit 100

echo "--- 首次爬取完成 ---"