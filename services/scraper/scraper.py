"""
Pakistani Fashion Product Scraper
───────────────────────────────────
Scrapes real product data from:
  - Khaadi (khaadi.com)
  - Sapphire (pk.sapphire.com.pk)
  - Alkaram (alkaramstudio.com)

Run this script ONCE to populate your Firebase products collection.
Then run it weekly to keep products fresh.

Usage:
    python -m services.scraper.scraper
"""

import time
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from services.firebase_service import save_products_batch

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─── Utility ───────────────────────────────────────────────────────────────────

def _make_product_id(brand: str, url: str) -> str:
    """Generate a stable unique ID for a product based on its URL."""
    hash_val = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    prefix = brand[:3].upper()
    return f"{prefix}-{hash_val}"


def _clean_price(price_str: str) -> int:
    """
    Extract integer price from strings like 'PKR 2,500', 'Rs. 1500', '10% off PKR 1,500'.
    Skips numbers under 200 to avoid catching discount percentages, ratings, etc.
    No valid Pakistani clothing item costs less than PKR 200.
    """
    import re
    numbers = re.findall(r"\b[\d,]+\b", price_str)
    for n in numbers:
        val = int(n.replace(",", ""))
        if val >= 200:
            return val
    return 0


# ─── Khaadi Scraper ────────────────────────────────────────────────────────────

def scrape_khaadi(max_pages: int = 3) -> List[Dict]:
    """Scrape women's and men's products from Khaadi."""
    products = []

    urls = [
        ("https://www.khaadi.com/pk/women/ready-to-wear/", "women"),
        ("https://www.khaadi.com/pk/men/", "men"),
    ]

    for base_url, gender in urls:
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            try:
                print(f"  Scraping Khaadi {gender} page {page}...")
                resp = SESSION.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Khaadi product cards
                cards = soup.select(".product-item, .grid-product, .card--product")
                if not cards:
                    # Try alternate selector
                    cards = soup.select("[class*='product']")

                for card in cards:
                    try:
                        name_el = card.select_one(".product-item__title, .grid-product__title, h3, h4")
                        price_el = card.select_one(".product-price, .price, [class*='price']")
                        img_el = card.select_one("img")
                        link_el = card.select_one("a")

                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        price_text = price_el.get_text(strip=True)
                        price = _clean_price(price_text)
                        image_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                        href = link_el.get("href", "") if link_el else ""
                        product_url = f"https://khaadi.com{href}" if href.startswith("/") else href

                        if not name or price == 0:
                            continue

                        product_id = _make_product_id("Khaadi", product_url or name)

                        products.append({
                            "product_id": product_id,
                            "name": name,
                            "brand": "Khaadi",
                            "category": _infer_category(name, gender),
                            "gender": gender,
                            "price": price,
                            "url": product_url,
                            "image_url": image_url,
                            "scraped_at": datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        continue

                time.sleep(1.5)  # Be polite to the server

            except Exception as e:
                print(f"  [ERROR] Khaadi page {page}: {e}")
                continue

    print(f"  Khaadi: {len(products)} products scraped")
    return products


# ─── Sapphire Scraper ──────────────────────────────────────────────────────────

def scrape_sapphire(max_pages: int = 3) -> List[Dict]:
    """Scrape products from Sapphire."""
    products = []

    urls = [
        ("https://pk.sapphireonline.pk/women-clothing/ready-to-wear/", "women"),
        ("https://pk.sapphireonline.pk/men/", "men"),
    ]

    for base_url, gender in urls:
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            try:
                print(f"  Scraping Sapphire {gender} page {page}...")
                resp = SESSION.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                cards = soup.select(".product-card, .grid-item, [class*='product-item']")

                for card in cards:
                    try:
                        name_el = card.select_one(".product-card__title, .product-name, h3, h4")
                        price_el = card.select_one(".price, .product-price, [class*='price']")
                        img_el = card.select_one("img")
                        link_el = card.select_one("a")

                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        price = _clean_price(price_el.get_text(strip=True))
                        image_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                        href = link_el.get("href", "") if link_el else ""
                        product_url = f"https://pk.sapphireonline.pk{href}" if href.startswith("/") else href

                        if not name or price == 0:
                            continue

                        product_id = _make_product_id("Sapphire", product_url or name)

                        products.append({
                            "product_id": product_id,
                            "name": name,
                            "brand": "Sapphire",
                            "category": _infer_category(name, gender),
                            "gender": gender,
                            "price": price,
                            "url": product_url,
                            "image_url": image_url,
                            "scraped_at": datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        continue

                time.sleep(1.5)

            except Exception as e:
                print(f"  [ERROR] Sapphire page {page}: {e}")
                continue

    print(f"  Sapphire: {len(products)} products scraped")
    return products


# ─── Alkaram Scraper ───────────────────────────────────────────────────────────

def scrape_alkaram(max_pages: int = 3) -> List[Dict]:
    """Scrape products from Alkaram Studio."""
    products = []

    urls = [
        ("https://alkaramstudio.com/collections/women", "women"),
        ("https://alkaramstudio.com/collections/men", "men"),
    ]

    for base_url, gender in urls:
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            try:
                print(f"  Scraping Alkaram {gender} page {page}...")
                resp = SESSION.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                cards = soup.select(".product-item, .product-card, [class*='product']")

                for card in cards:
                    try:
                        name_el = card.select_one("h2, h3, h4, .title, [class*='title'], [class*='name']")
                        price_el = card.select_one("[class*='price'], .amount")
                        img_el = card.select_one("img")
                        link_el = card.select_one("a")

                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        price = _clean_price(price_el.get_text(strip=True))
                        image_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                        href = link_el.get("href", "") if link_el else ""
                        product_url = f"https://alkaramstudio.com{href}" if href.startswith("/") else href

                        if not name or price == 0:
                            continue

                        product_id = _make_product_id("Alkaram", product_url or name)

                        products.append({
                            "product_id": product_id,
                            "name": name,
                            "brand": "Alkaram",
                            "category": _infer_category(name, gender),
                            "gender": gender,
                            "price": price,
                            "url": product_url,
                            "image_url": image_url,
                            "scraped_at": datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        continue

                time.sleep(1.5)

            except Exception as e:
                print(f"  [ERROR] Alkaram page {page}: {e}")
                continue

    print(f"  Alkaram: {len(products)} products scraped")
    return products


# ─── Category Inference ────────────────────────────────────────────────────────

def _infer_category(name: str, gender: str) -> str:
    """
    Infer category from product name.
    Returns a standardized category string.
    """
    name_lower = name.lower()

    category_keywords = {
        "shalwar kameez": ["shalwar", "kameez", "2-piece", "2 piece", "suit"],
        "kurta": ["kurta", "kurti"],
        "lawn suit": ["lawn", "3-piece", "3 piece", "unstitched"],
        "dress": ["dress", "frock", "gown", "maxi"],
        "shirt": ["shirt", "top", "blouse", "tee"],
        "trousers": ["trouser", "pants", "pant", "jeans"],
        "dupatta": ["dupatta", "scarf", "stole"],
        "saree": ["saree", "sari"],
        "jacket": ["jacket", "coat", "blazer"],
        "accessories": ["bag", "purse", "belt", "shoes", "sandal"],
    }

    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in name_lower:
                return category

    # Fallback by gender
    return "kurta" if gender == "women" else "shalwar kameez"


# ─── Main Runner ───────────────────────────────────────────────────────────────

def run_scraper():
    """
    Scrape all brands and save to Firebase.
    Run this from the project root: python -m services.scraper.scraper
    """
    print("=" * 50)
    print("Starting Pakistani Fashion Scraper")
    print("=" * 50)

    all_products = []

    print("\n[1/3] Scraping Khaadi...")
    all_products.extend(scrape_khaadi(max_pages=3))

    print("\n[2/3] Scraping Sapphire...")
    all_products.extend(scrape_sapphire(max_pages=3))

    print("\n[3/3] Scraping Alkaram...")
    all_products.extend(scrape_alkaram(max_pages=3))

    print(f"\n{'='*50}")
    print(f"Total products scraped: {len(all_products)}")

    if all_products:
        print("Saving to Firebase...")
        count = save_products_batch(all_products)
        print(f"✅ {count} products saved to Firebase!")
    else:
        print("⚠️  No products scraped. Check your internet connection and CSS selectors.")

    print("=" * 50)


if __name__ == "__main__":
    run_scraper()