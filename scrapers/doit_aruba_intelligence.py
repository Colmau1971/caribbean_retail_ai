"""
DOIT ARUBA RETAIL INTELLIGENCE
API ODATA VERSION

Uso:
python scrapers/doit_aruba_intelligence.py
"""

import re
import time
import base64
import requests
import pandas as pd
import sys

from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from brand_dictionary import infer_brand
from search_dictionary import get_market_search_terms


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")

OUTPUT_DIR = BASE_DIR / "outputs" / "aruba"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LMSTUDIO_DIR = BASE_DIR / "lmstudio" / "aruba"
LMSTUDIO_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")

COUNTRY = "Aruba"
RETAILER = "DOIT Aruba"

AWG_TO_USD = 1 / 1.79

BASE_URL = (
    "https://general.doit.aw:8048/APP/ODataV4/"
    "Company('Doit%20Center')/AppItemList"
)

AUTH_USER = "WEBAPI"
AUTH_PASS = "SSjvDC9FijvuYLlEp6w4UzHb9VTOAjCA+DWeHTcocjw="

AUTH_TOKEN = base64.b64encode(
    f"{AUTH_USER}:{AUTH_PASS}".encode()
).decode()

HEADERS = {
    "Authorization": f"Basic {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

SEARCH_TERMS = get_market_search_terms("Aruba")


# =========================================================
# HELPERS
# =========================================================

def clean_product_name(text):
    if not text:
        return None

    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 180:
        text = text[:180]

    return text


def normalize_barcode(value):
    if pd.isna(value) or value is None:
        return None

    value = str(value).strip().replace(".0", "")
    value = re.sub(r"[^0-9]", "", value)

    if not value:
        return None

    if len(value) == 11:
        return value.zfill(12)

    if len(value) in [12, 13, 14]:
        return value

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
        return round(convert_to_kg(qty * value, unit), 3)

    patterns = [
        (r"(\d+(?:\.\d+)?)\s?kg", "kg"),
        (r"(\d+(?:\.\d+)?)\s?g\b", "g"),
        (r"(\d+(?:\.\d+)?)\s?gr\b", "gr"),
        (r"(\d+(?:\.\d+)?)\s?oz\b", "oz"),
        (r"(\d+(?:\.\d+)?)\s?lb\b", "lb"),
        (r"(\d+(?:\.\d+)?)\s?lbs\b", "lbs"),
    ]

    for pattern, unit in patterns:
        match = re.search(pattern, text)

        if match:
            return round(
                convert_to_kg(float(match.group(1)), unit),
                3
            )

    return None


def classify_category(name, source_category):
    if not name:
        return source_category

    n = name.lower()

    if any(x in n for x in ["tortilla", "wrap", "flatbread"]):
        return "Tortillas & Wraps"

    if any(x in n for x in ["bread", "bun", "roll", "bagel", "loaf"]):
        return "Bakery"

    if any(x in n for x in ["cookie", "biscuit", "wafer", "oreo"]):
        return "Cookies"

    if any(x in n for x in ["cracker", "ritz"]):
        return "Crackers"

    if any(x in n for x in ["chips", "snack", "popcorn", "pretzel", "pringles", "doritos"]):
        return "Snacks"

    if any(x in n for x in ["frozen", "dough", "pizza"]):
        return "Frozen Bakery"

    return source_category


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


def safe_brand(api_brand, product_name):
    if api_brand and str(api_brand).strip():
        return str(api_brand).strip()

    detected = infer_brand(product_name)

    if detected:
        return detected

    return "Unknown"


def escape_odata_text(value):
    return str(value).replace("'", "''")


# =========================================================
# API SCRAPER
# =========================================================

def fetch_odata_products(keyword, top=100):
    keyword = escape_odata_text(keyword)

    params = {
        "$top": top,
        "$filter": (
            f"contains(Description,'{keyword}') "
            "and ShowonWebsite eq true"
        ),
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=45,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("value", [])


def scrape_search(category, keyword):
    print(
        f"Scraping DOIT Aruba | {category} | {keyword}"
    )

    try:
        items = fetch_odata_products(keyword)
    except Exception as e:
        print(f"ERROR API DOIT | {keyword}: {e}")
        return []

    products = []
    seen = set()

    for item in items:
        name = clean_product_name(
            item.get("Description")
        )

        if not name:
            continue

        price_awg = item.get("LSC_Unit_Price_Incl_VAT")

        try:
            price_awg = float(price_awg)
        except Exception:
            continue

        if price_awg <= 0:
            continue

        barcode = normalize_barcode(
            item.get("No")
        )

        weight_kg = estimate_weight_kg(name)

        price_usd = round(
            price_awg * AWG_TO_USD,
            2
        )

        price_per_kg_usd = None

        if weight_kg and weight_kg > 0:
            price_per_kg_usd = round(
                price_usd / weight_kg,
                2
            )

        brand = safe_brand(
            item.get("LSC_Attrib_1_Code"),
            name
        )

        product_url = (
            "https://doit.aw/search/?keyword="
            + keyword.replace(" ", "+")
        )

        key = (
            RETAILER,
            name,
            price_awg,
            barcode
        )

        if key in seen:
            continue

        seen.add(key)

        products.append(
            {
                "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "country": COUNTRY,
                "retailer": RETAILER,
                "category": classify_category(name, category),
                "source_category": category,
                "search_term": keyword,
                "brand": brand,
                "product_name": name,
                "barcode": barcode,
                "barcode_length": len(barcode) if barcode else None,
                "price_awg": round(price_awg, 2),
                "price_local": round(price_awg, 2),
                "currency": "AWG",
                "price_usd": price_usd,
                "presentation": item.get("Sales_Unit_of_Measure"),
                "weight_kg": weight_kg,
                "price_per_kg_usd": price_per_kg_usd,
                "segment": segment_product(price_usd),
                "product_url": product_url,
                "source_url": BASE_URL,
                "item_no": item.get("No"),
                "division_code": item.get("LSC_Division_Code"),
                "item_category_code": item.get("Item_Category_Code"),
                "retail_product_code": item.get("LSC_Retail_Product_Code"),
                "on_hand_qty": item.get("OnHandQty"),
                "show_on_website": item.get("ShowonWebsite"),
            }
        )

    print(f"  Productos encontrados: {len(products)}")

    return products


# =========================================================
# MAIN
# =========================================================

def main():
    all_products = []

    for category, keywords in SEARCH_TERMS.items():

        for keyword in keywords:

            products = scrape_search(
                category,
                keyword
            )

            all_products.extend(products)

            time.sleep(1)

    df = pd.DataFrame(all_products)

    if not df.empty:

        df["barcode"] = df["barcode"].apply(normalize_barcode)

        df["barcode_length"] = (
            df["barcode"]
            .astype("string")
            .str.len()
        )

        df = df.drop_duplicates(
            subset=[
                "retailer",
                "product_name",
                "price_usd",
                "barcode",
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

    latest_csv_path = (
        OUTPUT_DIR /
        "doit_aruba_retail_intelligence_latest.csv"
    )

    latest_excel_path = (
        OUTPUT_DIR /
        "doit_aruba_retail_intelligence_latest.xlsx"
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
    df.to_excel(latest_excel_path, index=False)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_csv(latest_csv_path, index=False, encoding="utf-8-sig")

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
    print(f"Latest Excel: {latest_excel_path}")
    print(f"Latest CSV: {latest_csv_path}")
    print(f"TXT: {txt_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()