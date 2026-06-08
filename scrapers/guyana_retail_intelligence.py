"""
GUYANA RETAIL INTELLIGENCE - MULTI RETAILER + BARCODE / UPC / GTIN + LOAD MORE
Massy Stores Guyana + Francis de Gossiper / Bounty Supermarket

Uso:
python scrapers/guyana_retail_intelligence.py
"""

import re
import time
import random
import requests
import pandas as pd
import matplotlib.pyplot as plt

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

from search_dictionary import get_market_search_terms

import undetected_chromedriver as uc


# =========================
# CONFIGURACIÓN GENERAL
# =========================

EXCHANGE_RATE_GYD_USD = 208.0

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")

OUTPUT_DIR = BASE_DIR / "outputs" / "guyana"
CHART_DIR = OUTPUT_DIR / "charts"
LMSTUDIO_DIR = BASE_DIR / "lmstudio" / "guyana"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)
LMSTUDIO_DIR.mkdir(parents=True, exist_ok=True)

MASSY_BASE_URL = "https://www.shopmassystoresgy.com"
FRANCIS_BOUNTY_URL = "https://francisdegossiper.com/store/bounty-supermarket/"

SEARCH_TERMS = get_market_search_terms("Guyana")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


# =========================
# URLS
# =========================

def build_massy_search_url(term: str) -> str:
    return (
        f"{MASSY_BASE_URL}/?s={term.replace(' ', '+')}"
        f"&post_type=product&dgwt_wcas=1"
    )


def build_francis_search_url(term: str, page: int = 1) -> str:
    if page <= 1:
        return (
            f"{FRANCIS_BOUNTY_URL}?s={term.replace(' ', '+')}"
            f"&post_type=product"
        )

    return (
        f"{FRANCIS_BOUNTY_URL}page/{page}/"
        f"?s={term.replace(' ', '+')}&post_type=product"
    )


# =========================
# DRIVER MASSY
# =========================

def start_driver():
    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,1200")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(
        options=options,
        version_main=148,
        use_subprocess=True
    )

    return driver


def click_load_more(driver, max_clicks=8):
    """
    Hace clic en botones Load More / Load more cuando existen.
    Esto ayuda a capturar más productos en Massy antes de leer el HTML.
    """

    for i in range(max_clicks):

        try:
            buttons = driver.find_elements(
                "xpath",
                "//*[contains(translate(normalize-space(text()), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'load more')]"
            )

            visible_buttons = [
                b for b in buttons
                if b.is_displayed()
            ]

            if not visible_buttons:
                print("No hay más Load More.")
                break

            button = visible_buttons[-1]

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                button
            )

            time.sleep(1)

            driver.execute_script(
                "arguments[0].click();",
                button
            )

            print(f"Load More click {i + 1}")

            time.sleep(4)

        except Exception as e:
            print(f"No pude hacer click en Load More: {e}")
            break


def page_source_with_selenium(driver, url: str):
    driver.get(url)

    time.sleep(5)

    for _ in range(3):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(1.5)

    click_load_more(
        driver,
        max_clicks=8
    )

    for _ in range(2):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(1.5)

    return driver.page_source


# =========================
# UTILIDADES
# =========================

def safe_get_text(el):
    return el.get_text(" ", strip=True) if el else None


def normalize_url(url: str, base: str):
    if not url:
        return None

    if url.startswith("http"):
        return url

    if url.startswith("/"):
        return base.rstrip("/") + url

    return base.rstrip("/") + "/" + url


def clean_price(price_text: str):
    if not price_text:
        return None

    text = price_text.replace(",", "")

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        text
    )

    return float(match.group(1)) if match else None


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


def product_matches_terms(product_name: str, terms):
    if not product_name:
        return False

    lower = product_name.lower()

    return any(
        term.lower() in lower
        for term in terms
    )


# =========================
# SCRAPER MASSY
# =========================

def extract_products_from_massy(driver, category: str, term: str):
    url = build_massy_search_url(term)

    print(f"Scraping Massy: {category} | {term} | {url}")

    try:
        html = page_source_with_selenium(driver, url)
        soup = BeautifulSoup(html, "lxml")

        debug_path = (
            OUTPUT_DIR /
            f"massy_debug_{category}_{term}.html"
            .replace(" ", "_")
            .replace("/", "_")
        )

        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)

        potential_barcodes = re.findall(r"\b\d{12,14}\b", html)

        print(
            "  Barcodes potenciales Massy HTML:",
            len(set(potential_barcodes))
        )

    except Exception as e:
        print(f"Error Massy {url}: {e}")
        return []

    products = parse_product_cards(
        soup=soup,
        retailer="Massy Stores Guyana",
        source_category=category,
        search_term=term,
        source_url=url,
        base_url=MASSY_BASE_URL
    )

    print(f"  Productos encontrados Massy: {len(products)}")

    return products


# =========================
# SCRAPER FRANCIS / BOUNTY
# =========================

def get_soup_requests(url: str):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(response.text, "lxml")


def extract_products_from_francis_bounty(
    category: str,
    term: str,
    max_pages: int = 3
):
    all_products = []

    for page in range(1, max_pages + 1):
        url = build_francis_search_url(term, page)

        print(
            f"Scraping Bounty/Francis: {category} | "
            f"{term} | page {page} | {url}"
        )

        try:
            soup = get_soup_requests(url)

        except Exception as e:
            print(f"Error Francis/Bounty {url}: {e}")

            if page == 1:
                try:
                    soup = get_soup_requests(FRANCIS_BOUNTY_URL)

                except Exception as e2:
                    print(f"Error fallback Francis/Bounty: {e2}")
                    return []
            else:
                break

        products = parse_product_cards(
            soup=soup,
            retailer="Bounty Supermarket / Francis de Gossiper",
            source_category=category,
            search_term=term,
            source_url=url,
            base_url="https://francisdegossiper.com"
        )

        category_terms = SEARCH_TERMS.get(category, [])

        filtered = [
            p for p in products
            if product_matches_terms(
                p.get("product_name"),
                [term] + category_terms
            )
        ]

        products = filtered if filtered else products

        print(
            f"  Productos encontrados Bounty/Francis: "
            f"{len(products)}"
        )

        all_products.extend(products)

        if not products:
            break

        time.sleep(random.uniform(1.2, 2.5))

    return all_products


# =========================
# PARSER GENÉRICO DE PRODUCTOS
# =========================

def parse_product_cards(
    soup,
    retailer: str,
    source_category: str,
    search_term: str,
    source_url: str,
    base_url: str
):
    products = []

    selectors = [
        "li.product",
        ".product",
        ".wc-block-grid__product",
        ".woocommerce-loop-product",
        ".store-product",
        ".product-item",
        ".item-product",
        ".products .type-product"
    ]

    cards = []

    for selector in selectors:
        cards = soup.select(selector)

        if cards:
            break

    if not cards:
        cards = soup.select(
            "a[href*='/product/'], a[href*='product']"
        )

    seen = set()

    for card in cards:

        if card.name == "a":
            link_el = card
            container = card.parent
        else:
            link_el = card.select_one("a[href]")
            container = card

        if container is None:
            continue

        name_el = (
            container.select_one("h2.woocommerce-loop-product__title")
            or container.select_one(".woocommerce-loop-product__title")
            or container.select_one(".wc-block-grid__product-title")
            or container.select_one(".product-title")
            or container.select_one(".product-name")
            or container.select_one("h2")
            or container.select_one("h3")
            or link_el
        )

        price_el = (
            container.select_one(".price")
            or container.select_one(".woocommerce-Price-amount")
            or container.select_one(".amount")
            or container.select_one("[class*='price']")
        )

        image_el = container.select_one("img")

        product_name = safe_get_text(name_el)
        price_text = safe_get_text(price_el)
        product_url = (
            normalize_url(link_el.get("href"), base_url)
            if link_el else None
        )
        product_detail_text = container.get_text(
            " ",
            strip=True
        )
        image_url = (
            normalize_url(image_el.get("src"), base_url)
            if image_el else None
        )

        price_gyd = clean_price(price_text)

        if not product_name or len(product_name) < 3:
            continue

        if product_name.lower() in [
            "add to cart",
            "select options",
            "read more",
            "quick view"
        ]:
            continue

        barcode = normalize_barcode(
            extract_barcode(str(container))
        )

        key = (
            retailer,
            product_name,
            price_gyd,
            product_url
        )

        if key in seen:
            continue

        seen.add(key)

        products.append({
            "scrape_date": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "retailer": retailer,
            "source_category": source_category,
            "search_term": search_term,
            "product_detail_text": product_detail_text,
            "product_name": product_name,
            "barcode": barcode,
            "barcode_length": (
                len(barcode)
                if barcode
                else None
            ),
            "price_text": price_text,
            "price_gyd": price_gyd,
            "product_url": product_url,
            "image_url": image_url,
            "source_url": source_url
        })

    return products


# =========================
# NORMALIZACIÓN
# =========================

def infer_brand(product_name: str):

    if not product_name:
        return None

    name_clean = (
        str(product_name)
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
        "club social": "Club Social",
        "tuc": "Tuc",

        # PEPSICO
        "lays": "Lays",
        "lay's": "Lays",
        "doritos": "Doritos",
        "cheetos": "Cheetos",
        "tostitos": "Tostitos",
        "pringles": "Pringles",
        "sun chips": "Sun Chips",

        # CAMPBELL
        "pepperidge": "Pepperidge Farm",
        "goldfish": "Goldfish",

        # GRUMA
        "mission": "Mission",

        # BIMBO / LATAM
        "marinela": "Marinela",
        "gamesa": "Gamesa",

        # TOUFAYAN
        "toufayan": "Toufayan",

        # REGIONALES
        "sunshine": "Sunshine",
        "crix": "Crix",
        "kiss": "Kiss",
        "holiday": "Holiday",

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
        "mcvitie": "McVitie",
        "kellogg": "Kellogg",
        "jumbo": "Jumbo",
        "stacy's": "Stacy's",
        "hershey": "Hershey",
        "cadbury": "Cadbury",
        "nestle": "Nestlé",
        "blue ribbon": "Blue Ribbon",
        "national": "National",
        "nissin": "Nissin",
        "diana": "Diana",
        "tosh": "Tosh",
        "excelsior": "Excelsior",

        # NEW BRANDS

        "colombina": "Colombina",
        "planters": "Planters",
        "snickers": "Snickers",
        "ovaltine": "Ovaltine",
        "mcvities": "McVitie's",
        "walkers": "Walkers",
        "glad": "Glad",
        "reynolds": "Reynolds",
        "toppers": "Toppers",
        "soldanza": "Soldanza",
        "motto": "Motto",
        "phidelia": "Phidelia",
        "whytes": "Whytes",
    }

    for keyword, brand in BRAND_KEYWORDS.items():

        if keyword in name_clean:
            return brand

    return "Other"


def convert_to_kg(value: float, unit: str):
    unit = unit.lower()

    if unit == "kg":
        return value

    if unit in ["g", "gr", "gram", "grams"]:
        return value / 1000

    if unit in ["oz", "ounce", "ounces"]:
        return value * 0.0283495

    if unit in ["lb", "lbs", "pound", "pounds"]:
        return value * 0.453592

    return None


def extract_weight_kg(product_name: str):
    if not product_name:
        return None

    text = product_name.lower().replace(",", ".")

    text = re.sub(
        r"\d+(?:\.\d+)?\s*[″\"]",
        " ",
        text
    )

    multi = re.search(
        r"(\d+)\s*[x×]\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(g|gr|gram|grams|kg|oz|lb|lbs)",
        text
    )

    if multi:
        qty = float(multi.group(1))
        value = float(multi.group(2))
        unit = multi.group(3)

        return convert_to_kg(
            qty * value,
            unit
        )

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(kg|g|gr|gram|grams|oz|ounce|ounces|lb|lbs|pound|pounds)",
        text
    )

    if match:
        return convert_to_kg(
            float(match.group(1)),
            match.group(2)
        )

    return None



def classify_segment(price_per_kg_usd):
    if price_per_kg_usd is None or pd.isna(price_per_kg_usd):
        return "Unclassified"

    if price_per_kg_usd < 4:
        return "Value"

    if price_per_kg_usd < 8:
        return "Mainstream"

    if price_per_kg_usd < 14:
        return "Premium"

    return "Super Premium"


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=[
            "retailer",
            "product_name",
            "price_gyd",
            "product_url"
        ]
    ).copy()

    df["country"] = "Guyana"
    df["currency"] = "GYD"

    if "barcode" in df.columns:
        df["barcode"] = df["barcode"].apply(normalize_barcode)
        df["barcode_length"] = df["barcode"].astype("string").str.len()

    df["brand"] = df["product_name"].apply(infer_brand)

    df["weight_source_text"] = (
        df["product_name"].fillna("")
        + " "
        + df["product_detail_text"].fillna("")
    )

    df["weight_kg"] = df["weight_source_text"].apply(
        extract_weight_kg
    )

    df["category"] = df["source_category"]

    df["commercial_category"] = df["source_category"]

    df["price_usd"] = df["price_gyd"] / EXCHANGE_RATE_GYD_USD

    df["price_per_kg_gyd"] = df.apply(
        lambda r: (
            r["price_gyd"] / r["weight_kg"]
            if pd.notna(r["price_gyd"])
            and pd.notna(r["weight_kg"])
            and r["weight_kg"] > 0
            else None
        ),
        axis=1
    )

    df["price_per_kg_usd"] = (
        df["price_per_kg_gyd"] / EXCHANGE_RATE_GYD_USD
    )

    df["segment"] = df["price_per_kg_usd"].apply(
        classify_segment
    )

    return df


# =========================
# INSIGHTS
# =========================

def create_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    return df.groupby(
        ["retailer", "commercial_category"]
    ).agg(
        skus=("product_name", "count"),
        brands=("brand", "nunique"),
        avg_price_gyd=("price_gyd", "mean"),
        avg_price_usd=("price_usd", "mean"),
        avg_price_per_kg_usd=("price_per_kg_usd", "mean"),
        min_price_per_kg_usd=("price_per_kg_usd", "min"),
        max_price_per_kg_usd=("price_per_kg_usd", "max")
    ).reset_index().sort_values(
        ["retailer", "skus"],
        ascending=[True, False]
    )


def create_alerts(df: pd.DataFrame) -> pd.DataFrame:
    alerts = []

    if df.empty:
        return pd.DataFrame(alerts)

    for (retailer, category), group in df.groupby(["retailer", "commercial_category"]):
        valid = group.dropna(subset=["price_per_kg_usd"])

        if valid.empty:
            continue

        avg = valid["price_per_kg_usd"].mean()

        for _, r in valid.iterrows():

            if r["price_per_kg_usd"] > avg * 1.35:
                alert_type = "Premium price gap"
                insight = (
                    "Producto con precio/kg superior al promedio; "
                    "posible techo premium."
                )

            elif r["price_per_kg_usd"] < avg * 0.75:
                alert_type = "Value price anchor"
                insight = (
                    "Producto con precio/kg bajo; posible ancla "
                    "competitiva de entrada."
                )

            else:
                continue

            alerts.append({
                "retailer": retailer,
                "alert_type": alert_type,
                "category": category,
                "brand": r["brand"],
                "product_name": r["product_name"],
                "barcode": r.get("barcode"),
                "price_per_kg_usd": r["price_per_kg_usd"],
                "category_avg_usd_kg": avg,
                "insight": insight
            })

    return pd.DataFrame(alerts)


# =========================
# EXPORT LM STUDIO / RAG LOCAL
# =========================

def safe_value(value, default="No disponible"):
    if pd.isna(value) or value is None or value == "":
        return default

    return value


def export_lmstudio_files(normalized_df: pd.DataFrame):
    if normalized_df.empty:
        return None, None, None

    lm_dir = OUTPUT_DIR / "lmstudio"
    lm_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    csv_path = lm_dir / f"guyana_master_clean_{timestamp}.csv"

    latest_csv = (
        lm_dir /
        "guyana_master_clean_latest.csv"
    )

    jsonl_path = lm_dir / f"guyana_products_rag_{timestamp}.jsonl"
    txt_path = lm_dir / f"guyana_products_rag_{timestamp}.txt"

    normalized_df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    normalized_df.to_csv(
        latest_csv,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Latest CSV: {latest_csv}")

    with open(jsonl_path, "w", encoding="utf-8") as f_jsonl:

        for _, r in normalized_df.iterrows():

            record = {
                "country": safe_value(r.get("country")),
                "retailer": safe_value(r.get("retailer")),
                "category": safe_value(r.get("category")),
                "source_category": safe_value(r.get("source_category")),
                "brand": safe_value(r.get("brand")),
                "product_name": safe_value(r.get("product_name")),
                "barcode": safe_value(r.get("barcode")),
                "price_gyd": (
                    None if pd.isna(r.get("price_gyd"))
                    else r.get("price_gyd")
                ),
                "price_usd": (
                    None if pd.isna(r.get("price_usd"))
                    else r.get("price_usd")
                ),
                "weight_kg": (
                    None if pd.isna(r.get("weight_kg"))
                    else r.get("weight_kg")
                ),
                "price_per_kg_usd": (
                    None if pd.isna(r.get("price_per_kg_usd"))
                    else r.get("price_per_kg_usd")
                ),
                "segment": safe_value(r.get("segment")),
                "product_url": safe_value(r.get("product_url")),
                "scrape_date": safe_value(r.get("scrape_date")),
            }

            f_jsonl.write(
                pd.Series(record).to_json(force_ascii=False)
                + "\n"
            )

    with open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(
            "GUYANA RETAIL INTELLIGENCE - PRODUCT DATABASE\n"
        )
        f_txt.write(
            "Base consolidada de productos capturados en retailers de Guyana.\n\n"
        )

        for idx, r in normalized_df.iterrows():
            f_txt.write(f"PRODUCTO {idx + 1}\n")
            f_txt.write(f"Country: {safe_value(r.get('country'))}\n")
            f_txt.write(f"Retailer: {safe_value(r.get('retailer'))}\n")
            f_txt.write(f"Categoría: {safe_value(r.get('category'))}\n")
            f_txt.write(f"Categoría fuente: {safe_value(r.get('source_category'))}\n")
            f_txt.write(f"Marca estimada: {safe_value(r.get('brand'))}\n")
            f_txt.write(f"Producto: {safe_value(r.get('product_name'))}\n")
            f_txt.write(f"Barcode: {safe_value(r.get('barcode'))}\n")
            f_txt.write(f"Precio público Guyana: {safe_value(r.get('price_gyd'))} GYD\n")
            f_txt.write(f"Precio estimado USD: {safe_value(r.get('price_usd'))}\n")
            f_txt.write(f"Peso estimado kg: {safe_value(r.get('weight_kg'))}\n")
            f_txt.write(f"Precio por kg USD: {safe_value(r.get('price_per_kg_usd'))}\n")
            f_txt.write(f"Segmento: {safe_value(r.get('segment'))}\n")
            f_txt.write(f"URL producto: {safe_value(r.get('product_url'))}\n")
            f_txt.write(f"Fecha captura: {safe_value(r.get('scrape_date'))}\n")
            f_txt.write(
                "Insight base: Este SKU puede usarse para comparar precio, "
                "arquitectura de portafolio, profundidad de surtido y "
                "oportunidad competitiva en Guyana.\n"
            )
            f_txt.write("---\n\n")

    return csv_path, jsonl_path, txt_path


# =========================
# GRÁFICOS Y EXCEL
# =========================

def create_charts(df: pd.DataFrame):
    valid = df.dropna(subset=["price_per_kg_usd"])

    if valid.empty:
        print("No hay datos suficientes para gráficos de precio/kg.")
        return

    cat_avg = (
        valid.groupby("category")["price_per_kg_usd"]
        .mean()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(10, 6))
    cat_avg.plot(kind="bar")
    plt.title("Guyana - Precio promedio USD/kg por categoría")
    plt.ylabel("USD/kg")
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "precio_promedio_usd_kg_categoria.png",
        dpi=160
    )
    plt.close()

    retailer_skus = (
        df.groupby("retailer")["product_name"]
        .count()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(10, 6))
    retailer_skus.plot(kind="bar")
    plt.title("Guyana - SKUs capturados por retailer")
    plt.ylabel("SKUs")
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "skus_por_retailer.png",
        dpi=160
    )
    plt.close()

    top_brands = (
        df.groupby("brand")["product_name"]
        .count()
        .sort_values(ascending=False)
        .head(15)
    )

    plt.figure(figsize=(10, 6))
    top_brands.plot(kind="bar")
    plt.title("Guyana - Top marcas por número de SKUs")
    plt.ylabel("SKUs")
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "top_marcas_skus.png",
        dpi=160
    )
    plt.close()


def export_excel(raw_df, normalized_df, summary_df, alerts_df):

    file_path = (
        OUTPUT_DIR /
        f"guyana_multi_retailer_intelligence_"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )

    latest_excel = (
        OUTPUT_DIR /
        "guyana_multi_retailer_intelligence_latest.xlsx"
    )

    with pd.ExcelWriter(
        file_path,
        engine="openpyxl"
    ) as writer:

        raw_df.to_excel(
            writer,
            sheet_name="Raw Data",
            index=False
        )

        normalized_df.to_excel(
            writer,
            sheet_name="Normalized",
            index=False
        )

        summary_df.to_excel(
            writer,
            sheet_name="Retailer Summary",
            index=False
        )

        alerts_df.to_excel(
            writer,
            sheet_name="Alerts",
            index=False
        )

        for sheet in writer.sheets.values():

            sheet.freeze_panes = "A2"

            for col in sheet.columns:

                max_len = max(
                    len(str(cell.value))
                    if cell.value is not None
                    else 0
                    for cell in col
                )

                sheet.column_dimensions[
                    col[0].column_letter
                ].width = min(
                    max_len + 2,
                    45
                )

    import shutil

    shutil.copy2(
        file_path,
        latest_excel
    )

    print(
        f"Latest Excel: {latest_excel}"
    )

    return file_path
# =========================
# MAIN
# =========================

def main():
    all_products = []

    driver = start_driver()

    try:
        for category, terms in SEARCH_TERMS.items():
            for term in terms:
                products = extract_products_from_massy(
                    driver,
                    category,
                    term
                )

                all_products.extend(products)

                time.sleep(random.uniform(1.8, 3.2))

    finally:
        driver.quit()

    for category, terms in SEARCH_TERMS.items():
        for term in terms:
            products = extract_products_from_francis_bounty(
                category,
                term,
                max_pages=3
            )

            all_products.extend(products)

            time.sleep(random.uniform(1.0, 2.2))

    raw_df = pd.DataFrame(all_products)

    if raw_df.empty:
        print(
            "No se encontraron productos. "
            "Revisa conexión, Cloudflare o estructura HTML del sitio."
        )
        return

    normalized_df = normalize_dataframe(raw_df)

    # ==========================================
    # REMOVE NON-PRODUCT RECORDS
    # ==========================================

    INVALID_PRODUCT_NAMES = {
        "Store Theme",
        "Grocery",
        "Produce",
        "Produce Misc",
        "Frozen Food",
        "Fresh Meat & Seafood",
        "Meat & Seafood",
        "Health",
        "Beauty",
        "Canned Products",
        "Boxed/Canned Meals",
        "DELI HOT",
        "DELI CUP",
        "DELI CUP LID",
        "DELI MEATS",
        "DELI MISC",
    }

    normalized_df = normalized_df[
        ~normalized_df["product_name"]
        .astype(str)
        .str.strip()
        .isin(INVALID_PRODUCT_NAMES)
    ]

    INVALID_PATTERNS = [
        r"^Fresh\s",
        r"^Produce",
        r"^Deli\s",
        r"^DELI",
        r"^Health",
        r"^Beauty",
    ]

    for pattern in INVALID_PATTERNS:

        normalized_df = normalized_df[
            ~normalized_df["product_name"]
            .astype(str)
            .str.contains(
                pattern,
                case=False,
                regex=True,
                na=False
            )
        ]

    print(
        f"Productos después limpieza Guyana: {len(normalized_df)}"
    )

    summary_df = create_summary(normalized_df)
    alerts_df = create_alerts(normalized_df)

    create_charts(normalized_df)

    csv_path, jsonl_path, txt_path = export_lmstudio_files(
        normalized_df
    )

    excel_path = export_excel(
        raw_df,
        normalized_df,
        summary_df,
        alerts_df
    )

    print("\n====================================")
    print(" GUYANA MULTI RETAILER INTELLIGENCE CREADO")
    print("====================================")
    print(f"Productos capturados raw: {len(raw_df)}")
    print(f"Productos normalizados: {len(normalized_df)}")
    print(f"Retailers: {normalized_df['retailer'].nunique()}")

    if "barcode" in normalized_df.columns:
        print("\nBarcodes encontrados:")
        print(
            normalized_df["barcode"]
            .notna()
            .sum()
        )

        print("\nDistribución barcode_length:")
        print(
            normalized_df["barcode_length"]
            .value_counts(dropna=False)
        )

    print(f"Excel: {excel_path}")
    print(f"CSV LM Studio: {csv_path}")
    print(f"JSONL RAG: {jsonl_path}")
    print(f"TXT RAG: {txt_path}")
    print(f"Gráficos: {CHART_DIR}")


if __name__ == "__main__":
    main()
