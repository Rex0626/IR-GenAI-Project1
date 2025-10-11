#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static scraper for Books to Scrape.
- Source: https://books.toscrape.com/
- Outputs: data/books_static_YYYYMMDD.csv
- Fields (example schema): id, source, title, url, author/vendor, category,
  date (YYYYMMDD), price/value, last_seen_at
- Features: robots.txt check, retry with exponential backoff (429/5xx),
  do NOT retry 404, dedup, date normalization, numeric validation, error logging.
"""

import argparse
import csv
import logging
import os
import random
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib import robotparser

# ---------------------- Config ----------------------
BASE_URL = "https://books.toscrape.com/"
CATALOG_PAGE = urljoin(BASE_URL, "catalogue/page-{}.html")
SOURCE_NAME = "books_toscrape"
VENDOR_NAME = "Books to Scrape"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

RE_PRICE = re.compile(r"[\d\.]+")

# ---------------------- Logging ----------------------
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("static_scraper")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/static_errors.log", encoding="utf-8")
fh.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
fh.setFormatter(fmt)
ch.setFormatter(fmt)
if not logger.handlers:
    logger.addHandler(fh)
    logger.addHandler(ch)
else:
    # Avoid duplicate handlers if reloaded
    logger.handlers = [fh, ch]

# ---------------------- Utilities ----------------------
def respectful_delay(min_s=0.8, max_s=1.7):
    """Randomized polite delay between requests."""
    time.sleep(random.uniform(min_s, max_s))


def can_fetch(url: str) -> bool:
    """Respect robots.txt."""
    rp = robotparser.RobotFileParser()
    robots_url = urljoin(BASE_URL, "robots.txt")
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception as e:
        logger.warning(f"robots.txt read failed ({robots_url}): {e}")
        # Conservative fallback: only allow within BASE_URL
        return url.startswith(BASE_URL)
    # Use our UA string as the user-agent for robots check
    return rp.can_fetch(UA, url)


def fetch_with_retry(url: str, session: requests.Session, max_tries: int = 5, base_delay: float = 1.0):
    """GET with exponential backoff on 429/5xx. Do NOT retry 404."""
    if not can_fetch(url):
        raise PermissionError(f"Disallowed by robots.txt: {url}")

    for i in range(max_tries):
        try:
            resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)

            if resp.status_code == 200:
                return resp

            # 404 = truly not found; don't retry
            if resp.status_code == 404:
                return resp

            # Retryable statuses
            if resp.status_code in (429, 500, 502, 503, 504):
                delay = base_delay * (2 ** i) + random.uniform(0, 0.5)
                logger.warning(f"{resp.status_code} on {url}; retry in {delay:.1f}s (attempt {i+1}/{max_tries})")
                time.sleep(delay)
                continue

            # Other non-retryable client errors (e.g., 403)
            resp.raise_for_status()
            return resp

        except requests.RequestException as e:
            # Network-level issues: retry with backoff
            delay = base_delay * (2 ** i) + random.uniform(0, 0.5)
            logger.warning(f"RequestException on {url}: {e}; retry in {delay:.1f}s (attempt {i+1}/{max_tries})")
            time.sleep(delay)

    raise RuntimeError(f"Failed after {max_tries} tries: {url}")


def normalize_date(dt: datetime) -> str:
    """Return YYYYMMDD string."""
    return dt.strftime("%Y%m%d")


def parse_price(text: str) -> float:
    """Extract numeric price as float. Raises ValueError if invalid."""
    m = RE_PRICE.search(text or "")
    if not m:
        raise ValueError(f"Invalid price text: {text}")
    return float(m.group())


def extract_book_list_items(html: str):
    """Parse a listing page and yield (title, href, price_text)."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.product_pod")
    for card in cards:
        a = card.select_one("h3 a")
        title = a.get("title") or a.text.strip()
        href = a.get("href")  # may be 'catalogue/xxx/index.html' or with ../
        price_text = (card.select_one(".price_color") or {}).get_text("", strip=True)
        yield title, href, price_text


def extract_detail_fields(html: str):
    """From a book detail page, return (id, category)."""
    soup = BeautifulSoup(html, "html.parser")

    # id: use table 'UPC' as stable unique id
    upc = None
    for row in soup.select("table.table.table-striped tr"):
        th = row.select_one("th")
        td = row.select_one("td")
        if th and td and th.text.strip().upper() == "UPC":
            upc = td.text.strip()
            break

    # category: breadcrumb (Home > Books > Category > Book)
    cat = None
    # Prefer last link before the current item (which is not a link)
    crumbs_links = soup.select("ul.breadcrumb li a")
    if len(crumbs_links) >= 2:
        cat = crumbs_links[-1].get_text(strip=True)
    if not cat:
        # fallback: use breadcrumb items
        bc_items = soup.select("ul.breadcrumb li")
        if len(bc_items) >= 3:
            cat = bc_items[-2].get_text(strip=True)

    return upc, (cat or "")


def resolve_detail_url(href: str, list_url: str) -> str:
    """
    Resolve product detail link robustly.
    Use the listing page URL as base so relative paths expand correctly.
    Guard: if '/catalogue/' vanished after join, re-insert it.
    """
    u = urljoin(list_url, href)  # base = listing page
    if "/catalogue/" not in u:
        # Keep only the tail after 'catalogue/' if present in href; otherwise use href tail
        tail = href.split("catalogue/")[-1].lstrip("./").lstrip("/")
        u = urljoin(BASE_URL, "catalogue/" + tail)
    return u


# ---------------------- Main scrape ----------------------
def scrape_books(num_pages: int = 5, outdir: str = "data") -> str:
    os.makedirs(outdir, exist_ok=True)
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    crawl_time = datetime.now()
    today = normalize_date(crawl_time)
    rows = []

    for page in range(1, num_pages + 1):
        list_url = CATALOG_PAGE.format(page)
        logger.info(f"Listing page {page}: {list_url}")
        respectful_delay()

        try:
            resp = fetch_with_retry(list_url, session)
        except Exception as e:
            logger.error(f"Failed listing page {page}: {e}")
            continue

        # Early stop: if no items found, we likely reached the end.
        items = list(extract_book_list_items(resp.text))
        if not items:
            logger.info(f"Reached end at page {page} (no items found).")
            break

        for title, href, price_text in items:
            # numeric validation for price
            try:
                price = parse_price(price_text)
            except Exception as e:
                logger.warning(f"Price parse failed ({price_text}) for title={title}: {e}")
                continue

            # Robust URL resolution for detail page
            detail_url = resolve_detail_url(href, list_url)
            respectful_delay()

            try:
                dresp = fetch_with_retry(detail_url, session)
                if dresp.status_code == 404:
                    logger.warning(f"Detail 404 (skip): {detail_url}")
                    continue
                upc, category = extract_detail_fields(dresp.text)
            except Exception as e:
                logger.warning(f"Detail parse failed {detail_url}: {e}")
                upc, category = None, ""  # still record minimal info

            rec_id = upc if upc else detail_url  # prefer UPC; fallback to URL

            row = {
                "id": rec_id,
                "source": SOURCE_NAME,
                "title": title,
                "url": detail_url,
                "author/vendor": VENDOR_NAME,  # site沒有作者欄，使用供應商
                "category": category,
                "date": today,           # 網站無發佈日，採用爬取日期
                "price/value": price,    # float
                "last_seen_at": today,   # 符合作業欄位
            }
            rows.append(row)

    if not rows:
        raise SystemExit("No rows scraped. Check connectivity or selectors.")

    # DataFrame + cleaning
    df = pd.DataFrame(rows, columns=[
        "id", "source", "title", "url", "author/vendor",
        "category", "date", "price/value", "last_seen_at"
    ])

    # Dedup by (source, id)
    before = len(df)
    df = df.drop_duplicates(subset=["source", "id"]).reset_index(drop=True)
    after = len(df)
    if after < before:
        logger.info(f"Deduplicated: {before - after} duplicates removed.")

    # Final numeric/date sanity
    for col in ("date", "last_seen_at"):
        bad_mask = ~df[col].astype(str).str.fullmatch(r"\d{8}")
        if bad_mask.any():
            n = int(bad_mask.sum())
            logger.warning(f"{col} has {n} invalid values; normalizing to crawl date {today}.")
            df.loc[bad_mask, col] = today

    # Save CSV
    out_path = os.path.join(outdir, f"books_static_{today}_p{num_pages}.csv")
    df.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info(f"Saved {len(df)} rows -> {out_path}")
    return out_path


# ---------------------- CLI ----------------------
def main():
    parser = argparse.ArgumentParser(description="Static scraper for Books to Scrape.")
    parser.add_argument("--pages", type=int, default=5, help="要爬的頁數（可配合 .sh 模擬增量：第一次5、第二次8）")
    parser.add_argument("--outdir", type=str, default="data", help="輸出資料夾")
    args = parser.parse_args()

    try:
        scrape_books(num_pages=args.pages, outdir=args.outdir)
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()