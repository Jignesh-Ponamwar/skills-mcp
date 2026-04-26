---
name: web-scraper
description: Scrape and extract structured content from websites. Handle pagination, dynamic JavaScript-rendered pages, rate limiting, and anti-bot measures. Use when the user needs to extract data from a website, scrape product listings, collect article text, or automate web data collection.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [web-scraping, html, beautifulsoup, playwright, requests, data-extraction]
  platforms: [claude-code, cursor, any]
  triggers:
    - scrape this website
    - extract data from this URL
    - web scraping
    - get data from this page
    - crawl this site
    - extract product listings
    - collect article text
    - parse HTML
    - automate web data collection
---

# Web Scraper Skill

## Overview
Extract structured data from websites responsibly. Choose the right tool based on whether the page is static HTML or requires JavaScript execution, then handle pagination, rate limiting, and data cleaning.

## Tool Selection

| Situation | Tool |
|-----------|------|
| Static HTML, simple pages | `requests` + `beautifulsoup4` |
| JS-rendered content (SPAs, React/Vue) | `playwright` or `selenium` |
| Heavy scraping / crawling | `scrapy` |
| API available | Use the API — always prefer it |

## Step-by-Step Process

### Step 1: Check for an API First
Before scraping, check:
- `robots.txt` at `site.com/robots.txt`
- The site's developer docs for a public API
- Network tab in DevTools — many "scraped" sites already have an XHR/fetch API

If an API exists, use it. It's faster, more reliable, and respectful.

### Step 2: Static HTML Scraping

```python
import requests
from bs4 import BeautifulSoup
import time

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0; +https://example.com/bot)"
}

response = requests.get("https://example.com/products", headers=headers, timeout=10)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# Find elements by CSS selector
items = soup.select("div.product-card")
for item in items:
    name = item.select_one("h2.product-name").get_text(strip=True)
    price = item.select_one("span.price").get_text(strip=True)
    link = item.select_one("a")["href"]
    print(name, price, link)
```

### Step 3: JavaScript-Rendered Pages

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com/spa-page", wait_until="networkidle")

    # Wait for dynamic content
    page.wait_for_selector("div.results")

    # Extract data
    items = page.query_selector_all("div.product-card")
    for item in items:
        name = item.query_selector("h2").inner_text()
        price = item.query_selector("span.price").inner_text()
        print(name, price)

    browser.close()
```

### Step 4: Handle Pagination

```python
import requests
from bs4 import BeautifulSoup

results = []
page = 1

while True:
    url = f"https://example.com/listings?page={page}"
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("div.item")
    if not items:
        break  # No more results

    for item in items:
        results.append(item.get_text(strip=True))

    next_btn = soup.select_one("a.next-page")
    if not next_btn:
        break

    page += 1
    time.sleep(1.5)  # Respectful delay between requests
```

### Step 5: Save and Clean the Data

```python
import pandas as pd
import re

df = pd.DataFrame(results)

# Clean price strings
df["price"] = df["price"].str.replace(r"[^\d.]", "", regex=True).astype(float)

# Normalize URLs
df["url"] = df["url"].apply(lambda u: u if u.startswith("http") else f"https://example.com{u}")

df.to_csv("scraped_data.csv", index=False)
```

## Rate Limiting and Politeness
- Always add delays: `time.sleep(1)` minimum between requests
- Respect `Crawl-delay` in `robots.txt`
- Set a descriptive `User-Agent` with contact info
- Don't send more than 1 request/second without explicit permission

## Anti-bot Countermeasures
- **429 Too Many Requests**: back off exponentially, add jitter
- **Cloudflare / bot detection**: use `playwright` with a real browser profile; avoid headless detection signatures
- **IP blocks**: rotate residential proxies if permitted by the site's ToS
- **CAPTCHAs**: do not attempt to bypass — respect the site's access controls

## Legal and Ethical Notes
- Only scrape publicly accessible data
- Don't scrape personal data (names, emails, phone numbers) without a legal basis
- Check the site's Terms of Service before scraping at scale
- Don't store or republish copyrighted content
