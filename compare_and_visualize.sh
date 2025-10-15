#!/bin/bash
echo "--- 首次執行爬蟲 ---"

# 執行靜態爬蟲，爬取 5 頁
python compare/src.py

# 執行動態爬蟲，爬取 5 頁
python compare/visualize_udn_report.py


echo "--- 首次爬取完成 ---"