"""
ARUBA RETAIL INTELLIGENCE
Fuente: Groceries To Go Aruba

Uso:
python aruba_retail_intelligence.py
"""

import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

BASE_URL = "https://groceriestogoaruba.com"
RETAILER = "Groceries To Go Aruba"
COUNTRY = "Aruba"

OUTPUT_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai/outputs/aruba")
LM_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai/lmstudio/aruba")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LM_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")

SEARCH_TERMS = {
    "Bakery": ["bread",  "bun", "bagel", "rolls"],
    "Tortillas & Wraps": ["tortilla", "tortillas", "wrap", "wraps", "flatbread"],
    "Cookies & Crackers": ["cookies", "biscuits", "crackers", "wafer", "wafers"],
    "Frozen Bakery": ["frozen bread", "frozen pizza"]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/148.0 Safari/537.36"
}


def build_search_url(term):
    return f"{BASE_URL}/search?type=product&options%5Bprefix%5D=last&q={term.replace(' ', '+')}"


def clean_price(text):
    if not text:
        return None
    text = text.replace(",", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    return float(match.group(1)) if match else None


def extract_weight_kg(name):
    if not name:
        return None

    text = name.lower().replace(",", ".")

    multi = re.search(r"(\d+)\s*[x×]\s*([0-9]+(?:\.[0-9]+)?)\s*(g|gr|kg|oz|lb|lbs)", text)
    if multi:
        qty = float(multi.group(1))
        value = float(multi.group(2))
        unit = multi.group(3)
        return convert_to_kg(qty * value, unit)

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gr|oz|lb|lbs)", text)
    if match:
        return convert_to_kg(float(match.group(1)), match.group(2))

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


def infer_brand(name):

    if not name:
        return None

    name_clean = (
        str(name)
        .lower()
        .replace("-", " ")
        .strip()
    )

    BRAND_KEYWORDS = {

        # BIMBO
        "tia rosa": "Tía Rosa",
        "sanissimo": "Saníssimo",
        "bimbo": "Bimbo",
        "takis": "Takis",

        # MONDELEZ
        "oreo": "Oreo",
        "ritz": "Ritz",
        "belvita": "Belvita",
        "chips ahoy": "Chips Ahoy",
        "triscuit": "Triscuit",

        # PEPSICO
        "lays": "Lays",
        "doritos": "Doritos",
        "cheetos": "Cheetos",
        "tostitos": "Tostitos",
        "pringles": "Pringles",

        # CAMPBELL
        "pepperidge": "Pepperidge Farm",
        "goldfish": "Goldfish",

        # GRUMA
        "mission": "Mission",

        # TOUFAYAN
        "toufayan": "Toufayan",

        # GENERAL
        "nature valley": "Nature Valley",
        "wonder": "Wonder",
        "sara lee": "Sara Lee",
        "thomas": "Thomas",
        "entenmann": "Entenmann",
        "old el paso": "Old El Paso",
        "quaker": "Quaker",
        "nabisco": "Nabisco",
        "bauducco": "Bauducco",
        
        # Bakery
        "food for life": "Food For Life",
        "ezekiel": "Food For Life",
        "dave's killer": "Dave's Killer Bread",
        "oroweat": "Oroweat",
        "brownberry": "Brownberry",
        
        # Cookies
        "wibisco": "Wibisco",
        "bermudez": "Bermudez",
        "colombina": "Colombina",
        "noel": "Noel",
        "devon": "Devon",
        
        # Snacks
        "ruffles": "Ruffles",
        "cheez it": "Cheez-It",
        "keebler": "Keebler",
        "planters": "Planters",
        
        # Frozen
        "eggo": "Eggo",
        }

    for keyword, brand in BRAND_KEYWORDS.items():

        if keyword in name_clean:
            return brand

    return "Other"


def classify_category(name, source_category):
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
    if "frozen" in n:
        return "Frozen Bakery"

    return source_category

def extract_barcode(html):

    if not html:
        return None

    patterns = [
        r'"gtin13"\s*:\s*"(\d+)"',
        r'"gtin12"\s*:\s*"(\d+)"',
        r'"gtin14"\s*:\s*"(\d+)"',
        r'"gtin"\s*:\s*"(\d+)"',
        r'"ean"\s*:\s*"(\d+)"',
        r'"upc"\s*:\s*"(\d+)"',
        r'"barcode"\s*:\s*"(\d+)"',
        r'"sku"\s*:\s*"(\d{8,14})"',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
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

def scrape_search(category, term):
    url = build_search_url(term)
    print(f"Scraping Aruba | {category} | {term} | {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=45)
        r.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")

    cards = (
        soup.select(".card-wrapper")
        or soup.select(".grid__item")
        or soup.select(".product-card")
        or soup.select("li.grid__item")
        or soup.select("a[href*='/products/']")
    )

    products = []
    seen = set()

    for card in cards:
        link = card if card.name == "a" else card.select_one("a[href*='/products/']")
        if not link:
            continue

        product_url = link.get("href")
        if product_url and product_url.startswith("/"):
            product_url = BASE_URL + product_url

        name_el = (
            card.select_one(".card__heading")
            or card.select_one(".full-unstyled-link")
            or card.select_one("h3")
            or link
        )

        price_el = (
            card.select_one(".price")
            or card.select_one(".price-item")
            or card.select_one("[class*='price']")
        )

        name = name_el.get_text(" ", strip=True) if name_el else None

        if name:
        
            # Remover prefijos tipo:
            # ƒ7.49 | 13 oz ...
            # ƒ3.49 | each ...
            # ƒ4.99 | 225 gram ...
        
            name = re.sub(
                r"^ƒ\s*\d+(?:\.\d+)?\s*\|\s*",
                "",
                name
            )
        
            # Remover unidades iniciales sueltas
            name = re.sub(
                r"^(each|[0-9]+(?:\.[0-9]+)?\s*(oz|gram|g|kg|lb|lbs|st))\s+",
                "",
                name,
                flags=re.IGNORECASE
            )

        name = re.sub(r"\s+", " ", name).strip()
        price_text = price_el.get_text(" ", strip=True) if price_el else None
        price_awg = clean_price(price_text)

        if not name or len(name) < 3:
            continue

        key = (name, price_awg, product_url)
        if key in seen:
            continue
        seen.add(key)

        barcode = None
            
        if product_url:
            try:
                product_page = requests.get(
                    product_url,
                    headers=HEADERS,
                    timeout=30
                )
                barcode = extract_barcode(product_page.text)
            except Exception:
                barcode = None

        weight_kg = extract_weight_kg(name)
        price_usd = price_awg / 1.79 if price_awg else None
        price_per_kg_usd = price_usd / weight_kg if price_usd and weight_kg else None

        products.append({
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "country": COUNTRY,
            "retailer": RETAILER,
            "source_category": category,
            "search_term": term,
            "category": classify_category(name, category),
            "brand": infer_brand(name),
            "product_name": name,
            "barcode": barcode,
            "price_text": price_text,
            "price_local": price_awg,
            "currency": "AWG",
            "price_usd": price_usd,
            "weight_kg": weight_kg,
            "price_per_kg_usd": price_per_kg_usd,
            "product_url": product_url,
            "source_url": url
        })

    print(f"  Productos encontrados Aruba: {len(products)}")
    return products

def export_lmstudio(df):
    txt_path = LM_DIR / f"aruba_products_rag_{TIMESTAMP}.txt"
    csv_path = LM_DIR / f"aruba_master_clean_{TIMESTAMP}.csv"
    latest_csv = LM_DIR / "aruba_master_clean_latest.csv"
    jsonl_path = LM_DIR / f"aruba_products_rag_{TIMESTAMP}.jsonl"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_csv(latest_csv, index=False, encoding="utf-8-sig")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("ARUBA RETAIL INTELLIGENCE DATABASE\n\n")

        for idx, r in df.iterrows():
            f.write(f"PRODUCT {idx + 1}\n")
            f.write(f"Country: Aruba\n")
            f.write(f"Retailer: {r.get('retailer', '')}\n")
            f.write(f"Category: {r.get('category', '')}\n")
            f.write(f"Brand: {r.get('brand', '')}\n")
            f.write(f"Product: {r.get('product_name', '')}\n")
            f.write(f"Price Local AWG: {r.get('price_local', '')}\n")
            f.write(f"Price USD: {r.get('price_usd', '')}\n")
            f.write(f"Weight KG: {r.get('weight_kg', '')}\n")
            f.write(f"Price per KG USD: {r.get('price_per_kg_usd', '')}\n")
            f.write("Strategic Role: Aruba premium tourism retail benchmark.\n")
            f.write("---\n\n")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for _, r in df.iterrows():
            f.write(r.to_json(force_ascii=False) + "\n")

    print(f"Latest CSV: {latest_csv}")

    return csv_path, txt_path, jsonl_path


def main():
    all_products = []

    for category, terms in SEARCH_TERMS.items():
        for term in terms:
            all_products.extend(scrape_search(category, term))
            time.sleep(1.5)

    df = pd.DataFrame(all_products)

    if df.empty:
        print("No se encontraron productos.")
        return
    if "barcode" in df.columns:
    
        df["barcode"] = df["barcode"].apply(normalize_barcode)
    
        df["barcode_length"] = (
            df["barcode"]
            .astype("string")
            .str.len()
        )
        
    df = df.drop_duplicates(subset=["product_name", "price_local", "product_url"])

    excel_path = OUTPUT_DIR / f"aruba_retail_intelligence_{TIMESTAMP}.xlsx"
    csv_path = OUTPUT_DIR / f"aruba_retail_intelligence_{TIMESTAMP}.csv"

    latest_excel = OUTPUT_DIR / "aruba_retail_intelligence_latest.xlsx"
    latest_csv = OUTPUT_DIR / "aruba_retail_intelligence_latest.csv"

    df.to_excel(excel_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    df.to_excel(latest_excel, index=False)
    df.to_csv(latest_csv, index=False, encoding="utf-8-sig")

    lm_csv, lm_txt, lm_jsonl = export_lmstudio(df)

    print("\n====================================")
    print(" ARUBA RETAIL INTELLIGENCE CREADO")
    print("====================================")
    
    print(f"Productos normalizados: {len(df)}")
    
    if "barcode" in df.columns:
        print(
            "Barcodes encontrados:",
            df["barcode"].notna().sum()
        )
    
    print(f"Excel: {excel_path}")
    print(f"CSV: {csv_path}")
    print(f"CSV LM Studio: {lm_csv}")
    print(f"TXT RAG: {lm_txt}")
    print(f"JSONL RAG: {lm_jsonl}")
    print(f"Latest Excel: {latest_excel}")
    print(f"Latest CSV: {latest_csv}")


if __name__ == "__main__":
    main()
