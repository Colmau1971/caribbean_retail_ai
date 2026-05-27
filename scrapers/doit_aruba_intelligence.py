"""
DOIT ARUBA RETAIL INTELLIGENCE
FINAL VERSION + BARCODE / UPC / GTIN

Uso:
python scrapers/doit_aruba_intelligence.py
"""

import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")

OUTPUT_DIR = BASE_DIR / "outputs" / "aruba"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LMSTUDIO_DIR = BASE_DIR / "lmstudio" / "aruba"
LMSTUDIO_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")

BASE_URL = "https://doit.aw"
RETAILER = "DOIT Aruba"
COUNTRY = "Aruba"

USD_TO_AWG = 1.79

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}

SEARCH_TERMS = {
    "Bakery": [
        "bread",
        "bun",
        "bagel",
        "roll"
    ],

    "Tortillas & Wraps": [
        "tortilla",
        "wrap",
        "flatbread"
    ],

    "Cookies & Crackers": [
        "cookies",
        "crackers",
        "wafer"
    ],

    "Snacks": [
        "chips",
        "snacks",
        "pretzels"
    ],

    "Frozen Bakery": [
        "frozen bread",
        "frozen dough",
        "frozen pizza"
    ]
}


# =========================================================
# HELPERS
# =========================================================

def build_search_url(keyword):
    return (
        f"{BASE_URL}/search/"
        f"?keyword={keyword.replace(' ', '+')}&CloseOut=null"
    )


def extract_price(text):
    if not text:
        return None

    patterns = [
        r"\$\s*([0-9]+(?:\.[0-9]+)?)",
        r"USD\s*([0-9]+(?:\.[0-9]+)?)",
        r"AWG\s*([0-9]+(?:\.[0-9]+)?)",
        r"Afl\.?\s*([0-9]+(?:\.[0-9]+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def extract_barcode(text):
    if not text:
        return None

    patterns = [
        r'"gtin13"\s*:\s*"?(\d+)"?',
        r'"gtin12"\s*:\s*"?(\d+)"?',
        r'"gtin14"\s*:\s*"?(\d+)"?',
        r'"gtin"\s*:\s*"?(\d+)"?',
        r'"ean"\s*:\s*"?(\d+)"?',
        r'"upc"\s*:\s*"?(\d+)"?',
        r'"barcode"\s*:\s*"?(\d+)"?',
        r'"sku"\s*:\s*"?(\d{8,14})"?',
        r'\b(\d{12})\b',
        r'\b(\d{13})\b',
        r'\b(\d{14})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return str(match.group(1))

    return None


def normalize_barcode(value):
    if pd.isna(value) or value is None:
        return None

    value = str(value).strip().replace(".0", "")

    if not value.isdigit():
        return None

    if len(value) == 11:
        return value.zfill(12)

    if len(value) in [12, 13, 14]:
        return value

    return value


def estimate_weight_kg(name):
    if not isinstance(name, str):
        return None

    text = name.lower().replace(",", ".")

    multi = re.search(
        r"(\d+)\s*[x×]\s*([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gr|oz|lb|lbs)",
        text
    )

    if multi:
        qty = float(multi.group(1))
        value = float(multi.group(2))
        unit = multi.group(3)
        return convert_to_kg(qty * value, unit)

    patterns = [
        (r"(\d+(?:\.\d+)?)\s?kg", 1),
        (r"(\d+(?:\.\d+)?)\s?g", 0.001),
        (r"(\d+(?:\.\d+)?)\s?gr", 0.001),
        (r"(\d+(?:\.\d+)?)\s?oz", 0.0283495),
        (r"(\d+(?:\.\d+)?)\s?lb", 0.453592),
        (r"(\d+(?:\.\d+)?)\s?lbs", 0.453592),
    ]

    for pattern, factor in patterns:
        match = re.search(pattern, text)

        if match:
            return round(float(match.group(1)) * factor, 3)

    return None


def convert_to_kg(value, unit):
    unit = unit.lower()

    if unit == "kg":
        return value
    if unit in ["g", "gr"]:
        return value / 1000
    if unit == "oz":
        return value * 0.0283495
    if unit in ["lb", "lbs"]:
        return value * 0.453592

    return None


def estimate_brand(name):
    if not isinstance(name, str) or not name.strip():
        return "Unknown"

    known = [
        "Oreo", "Nabisco", "Ritz", "Mission", "Toufayan", "Bimbo",
        "Tia Rosa", "Sara Lee", "Wonder", "Nature Valley", "Pringles",
        "Doritos", "Lays", "Lay's", "Quaker", "Pepperidge", "Thomas",
        "Entenmann", "Old El Paso", "McVitie", "Kellogg", "Belvita",
        "Goldfish", "Stacy's", "Jumbo"
    ]

    lower = name.lower()

    for brand in known:
        if brand.lower() in lower:
            return brand

    return name.split()[0]


def segment_product(price_usd):
    if pd.isna(price_usd):
        return "Unknown"

    if price_usd < 3:
        return "Value"

    if price_usd < 7:
        return "Mainstream"

    if price_usd < 12:
        return "Premium"

    return "Super Premium"


def clean_product_name(text):
    if not text:
        return None

    text = re.sub(r"\s+", " ", text).strip()

    cleanup_terms = [
        "Add to cart",
        "Add To Cart",
        "View product",
        "Quick view",
        "In stock",
        "Out of stock",
    ]

    for term in cleanup_terms:
        text = text.replace(term, "")

    text = text.strip()

    if len(text) > 180:
        text = text[:180]

    return text


def classify_category(name, source_category):
    if not name:
        return source_category

    n = name.lower()

    if any(x in n for x in ["tortilla", "wrap", "flatbread"]):
        return "Tortillas & Wraps"

    if any(x in n for x in ["bread", "bun", "roll", "bagel", "loaf"]):
        return "Bakery"

    if any(x in n for x in ["cookie", "biscuit", "wafer"]):
        return "Cookies"

    if "cracker" in n:
        return "Crackers"

    if any(x in n for x in ["chips", "snack", "popcorn", "pretzel"]):
        return "Snacks"

    if any(x in n for x in ["frozen", "dough", "pizza"]):
        return "Frozen Bakery"

    return source_category


def get_product_url(card, search_url):
    link = card.select_one("a[href]")

    if not link:
        return search_url

    href = link.get("href")

    if not href:
        return search_url

    return urljoin(BASE_URL, href)


def extract_product_name_from_card(card, text):
    selectors = [
        ".product-title",
        ".product-name",
        ".title",
        "h2",
        "h3",
        "h4",
        "a[href]"
    ]

    for selector in selectors:
        el = card.select_one(selector)
        if el:
            name = el.get_text(" ", strip=True)
            if name and len(name) > 2:
                return clean_product_name(name)

    # fallback: remueve precio del texto
    text = re.sub(r"\$\s*[0-9]+(?:\.[0-9]+)?", "", text)
    return clean_product_name(text)


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def extract_barcode_from_product_page(product_url):
    if not product_url or product_url == BASE_URL:
        return None

    try:
        html = get_html(product_url)
        return normalize_barcode(extract_barcode(html))
    except Exception:
        return None


# =========================================================
# SCRAPER
# =========================================================

def scrape_search(category, keyword):
    url = build_search_url(keyword)

    print(f"Scraping DOIT Aruba | {category} | {keyword} | {url}")

    try:
        html = get_html(url)
    except Exception as e:
        print(f"ERROR URL: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    cards = (
        soup.select(".product")
        or soup.select(".product-card")
        or soup.select(".product-item")
        or soup.select("[class*='product']")
        or soup.select("a[href*='product']")
        or soup.find_all("div")
    )

    products = []
    seen = set()
    found = 0

    for card in cards:
        text = card.get_text(" ", strip=True)

        if not text:
            continue

        if "$" not in text and "AWG" not in text and "Afl" not in text:
            continue

        price = extract_price(text)

        if not price:
            continue

        product_url = get_product_url(card, url)

        name = extract_product_name_from_card(card, text)

        if not name or len(name) < 3:
            continue

        if any(
            bad in name.lower()
            for bad in [
                "search",
                "cart",
                "login",
                "wishlist",
                "checkout",
                "navigation"
            ]
        ):
            continue

        barcode = normalize_barcode(
            extract_barcode(str(card))
        )

        if not barcode and product_url != url:
            barcode = extract_barcode_from_product_page(product_url)

        weight_kg = estimate_weight_kg(name)

        price_per_kg = None

        if weight_kg and weight_kg > 0:
            price_per_kg = round(price / weight_kg, 2)

        key = (
            RETAILER,
            name,
            price,
            product_url
        )

        if key in seen:
            continue

        seen.add(key)

        product = {
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "country": COUNTRY,
            "retailer": RETAILER,
            "category": classify_category(name, category),
            "source_category": keyword,
            "brand": estimate_brand(name),
            "product_name": name,
            "barcode": barcode,
            "barcode_length": len(barcode) if barcode else None,
            "price_awg": round(price * USD_TO_AWG, 2),
            "price_local": round(price * USD_TO_AWG, 2),
            "currency": "AWG",
            "price_usd": round(price, 2),
            "weight_kg": weight_kg,
            "price_per_kg_usd": price_per_kg,
            "segment": segment_product(price),
            "product_url": product_url,
            "source_url": url,
        }

        products.append(product)

        found += 1

    print(f"  Productos encontrados: {found}")

    return products


def main():
    all_products = []

    for category, keywords in SEARCH_TERMS.items():

        for keyword in keywords:

            products = scrape_search(
                category,
                keyword
            )

            all_products.extend(products)

            time.sleep(2)

    df = pd.DataFrame(all_products)

    if not df.empty:

        if "barcode" in df.columns:
            df["barcode"] = df["barcode"].apply(normalize_barcode)
            df["barcode_length"] = df["barcode"].astype("string").str.len()

        df = df.drop_duplicates(
            subset=[
                "retailer",
                "product_name",
                "price_usd",
                "product_url"
            ]
        )

    print("\n====================================")
    print(" DOIT ARUBA SCRAPER")
    print("====================================")
    print(f"Productos normalizados: {len(df)}")

    if not df.empty and "barcode" in df.columns:
        print("Barcodes encontrados:", df["barcode"].notna().sum())
        print("\nDistribución barcode_length:")
        print(df["barcode_length"].value_counts(dropna=False))

    excel_path = (
        OUTPUT_DIR /
        f"doit_aruba_retail_intelligence_{TIMESTAMP}.xlsx"
    )

    csv_path = (
        OUTPUT_DIR /
        f"doit_aruba_retail_intelligence_{TIMESTAMP}.csv"
    )

    txt_path = (
        LMSTUDIO_DIR /
        f"doit_aruba_products_rag_{TIMESTAMP}.txt"
    )

    jsonl_path = (
        LMSTUDIO_DIR /
        f"doit_aruba_products_rag_{TIMESTAMP}.jsonl"
    )

    df.to_excel(excel_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with open(txt_path, "w", encoding="utf-8") as f:

        f.write("DOIT ARUBA RETAIL INTELLIGENCE\n\n")

        for idx, row in df.iterrows():

            f.write(f"PRODUCT {idx + 1}\n")

            for col in df.columns:
                f.write(f"{col}: {row.get(col, '')}\n")

            f.write("---\n\n")

    with open(jsonl_path, "w", encoding="utf-8") as f:

        for _, row in df.iterrows():

            record = row.to_dict()

            f.write(
                pd.Series(record).to_json(force_ascii=False)
                + "\n"
            )

    print(f"Excel: {excel_path}")
    print(f"CSV: {csv_path}")
    print(f"TXT: {txt_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()
