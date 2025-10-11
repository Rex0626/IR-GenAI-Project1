#!/bin/bash
echo "--- 首次執行爬蟲 ---"

# 執行靜態爬蟲，爬取 5 頁
python src/scrape_static.py --pages 5

# 執行動態爬蟲，爬取 5 頁
python src/scrape_dynamic.py --pages 5

echo "--- 首次爬取完成 ---"