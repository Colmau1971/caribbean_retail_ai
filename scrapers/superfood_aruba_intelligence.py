"""
SUPER FOOD ARUBA RETAIL INTELLIGENCE
FINAL VERSION
- Selenium
- Multi-page scraping
- Barcode / UPC / GTIN extraction
- Aruba price normalization
- Product block segmentation
- LM Studio exports
"""

import re
import time
import pandas as pd

from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By


BASE_URL = "https://shop.superfoodaruba.com"

RETAILER = "Super Food Aruba"
COUNTRY = "Aruba"

BASE_DIR = Path(
    "/Users/mauriciogonzalez/Documents/caribbean_retail_ai"
)

OUTPUT_DIR = BASE_DIR / "outputs" / "aruba"
LM_DIR = BASE_DIR / "lmstudio" / "aruba"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LM_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")

MAX_PAGES = 6


SEARCH_TERMS = {
    "Bakery": [
        "bread"
    ],

    "Tortillas & Wraps": [
        "tortilla",
        "wrap"
    ],

    "Cookies & Crackers": [
        "cookies",
        "crackers"
    ],

    "Snacks": [
        "chips"
    ],

    "Frozen Bakery": [
        "frozen"
    ],
}


def start_driver():

    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")

    driver = uc.Chrome(
        options=options,
        version_main=148,
        use_subprocess=True,
    )

    return driver

def build_search_url(term):

    return (
        f"{BASE_URL}/shop#!/?q="
        f"{term.replace(' ', '+')}"
    )


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

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return str(match.group(1))

    return None


def normalize_barcode(value):

    if pd.isna(value) or value is None:
        return None

    value = (
        str(value)
        .strip()
        .replace(".0", "")
    )

    if not value.isdigit():
        return None

    if len(value) == 11:
        return value.zfill(12)

    if len(value) in [12, 13, 14]:
        return value

    return value


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


def extract_weight_kg(name):

    if not name:
        return None

    text = (
        name.lower()
        .replace(",", ".")
    )

    multi = re.search(
        r"(\d+)\s*[x×]\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(g|gr|kg|oz|lb|lbs)",
        text,
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
        r"(kg|g|gr|oz|lb|lbs)",
        text,
    )

    if match:

        return convert_to_kg(
            float(match.group(1)),
            match.group(2),
        )

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
        "mcvitie": "McVitie",
        "kellogg": "Kellogg",
        "jumbo": "Jumbo",
        "stacy's": "Stacy's",
    }

    for keyword, brand in BRAND_KEYWORDS.items():

        if keyword in name_clean:
            return brand

    return "Other"


def classify_category(name, source_category):

    if not name:
        return source_category

    n = name.lower()

    if any(
        x in n
        for x in [
            "tortilla",
            "wrap",
            "flatbread"
        ]
    ):
        return "Tortillas & Wraps"

    if any(
        x in n
        for x in [
            "bread",
            "bun",
            "roll",
            "bagel",
            "loaf",
            "baguette"
        ]
    ):
        return "Bakery"

    if any(
        x in n
        for x in [
            "cookie",
            "biscuit",
            "wafer"
        ]
    ):
        return "Cookies"

    if "cracker" in n:
        return "Crackers"

    if any(
        x in n
        for x in [
            "chips",
            "snack",
            "popcorn",
            "pretzel"
        ]
    ):
        return "Snacks"

    if "frozen" in n:
        return "Frozen Bakery"

    return source_category


def clean_product_name(text):

    if not text:
        return None

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    cleanup = [
        "Remove from List",
        "Add to Cart",
        "Add to cart",
        "Sale price",
    ]

    for c in cleanup:
        text = text.replace(c, "")

    text = text.strip()

    if len(text) > 180:
        text = text[:180]

    return text


def scroll_page(driver):

    for _ in range(4):

        try:

            driver.execute_script(
                "window.scrollTo("
                "0, document.body.scrollHeight);"
            )

            time.sleep(2)

        except Exception:
            break


def go_to_page(driver, page):

    if page <= 1:
        return True

    try:

        buttons = driver.find_elements(
            By.XPATH,
            f"//*[normalize-space(text())='{page}']"
        )

        if not buttons:
            print(f"No encontré página {page}")
            return False

        button = buttons[-1]

        driver.execute_script(
            "arguments[0].scrollIntoView("
            "{block: 'center'});",
            button
        )

        time.sleep(1)

        driver.execute_script(
            "arguments[0].click();",
            button
        )

        time.sleep(6)

        return True

    except Exception as e:

        print(f"No pude abrir página {page}: {e}")

        return False


def parse_products_from_html(
    html,
    category,
    term,
    source_url,
    page,
):

    products = []
    seen = set()

    product_blocks = re.split(
        r"(?=ƒ\s*[0-9]+(?:\.[0-9]+)?)",
        html
    )

    for block in product_blocks:

        text = BeautifulSoup(
            block,
            "lxml"
        ).get_text(
            " ",
            strip=True
        )

        if not text or len(text) < 5:
            continue

        lower = text.lower()

        hard_noise = [
            "items filters",
            "filters per page",
            "did you mean",
            "manage cookie consent",
            "accept cookies",
            "view preferences",
            "privacy policy",
        ]

        if any(
            n in lower
            for n in hard_noise
        ):
            continue

        price_match = re.search(
            r"ƒ\s*([0-9]+(?:\.[0-9]+)?)",
            text,
        )

        if not price_match:
            continue

        price_local = float(
            price_match.group(1)
        )

        name = clean_product_name(text)

        if not name:
            continue

        barcode = normalize_barcode(
            extract_barcode(block)
        )

        key = (
            name,
            price_local,
            barcode,
            page
        )

        if key in seen:
            continue

        seen.add(key)

        weight_kg = extract_weight_kg(name)

        price_usd = (
            price_local / 1.79
            if price_local
            else None
        )

        price_per_kg_usd = (
            price_usd / weight_kg
            if price_usd and weight_kg
            else None
        )

        products.append(
            {
                "scrape_date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

                "country": COUNTRY,
                "retailer": RETAILER,

                "source_category": category,
                "search_term": term,

                "page": page,

                "category": classify_category(
                    name,
                    category
                ),

                "brand": infer_brand(name),

                "product_name": name,

                "barcode": barcode,

                "barcode_length": (
                    len(barcode)
                    if barcode
                    else None
                ),

                "price_local": price_local,
                "currency": "AWG",

                "price_usd": price_usd,

                "weight_kg": weight_kg,

                "price_per_kg_usd": (
                    price_per_kg_usd
                ),

                "product_url": source_url,
                "source_url": source_url,
            }
        )

    return products


def scrape_search(
    driver,
    category,
    term,
):

    url = build_search_url(term)

    print(
        f"Scraping Super Food Aruba | "
        f"{category} | {term} | {url}"
    )

    try:

        driver.get(url)

    except Exception as e:

        print(f"Navigation failed: {e}")

        return []

    time.sleep(10)

    all_products = []

    for page in range(
        1,
        MAX_PAGES + 1
    ):

        print(f"Procesando página {page}")

        if page > 1:

            ok = go_to_page(
                driver,
                page
            )

            if not ok:
                break

        scroll_page(driver)

        try:

            html = driver.page_source

        except Exception as e:

            print(
                f"Could not read page source: {e}"
            )

            break

        debug_path = (
            OUTPUT_DIR /
            f"superfood_debug_page_{page}.html"
        )

        with open(
            debug_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)

        potential_barcodes = re.findall(
            r"\b\d{12,14}\b",
            html
        )

        print(
            f"Barcodes potenciales HTML página "
            f"{page}: "
            f"{len(set(potential_barcodes))}"
        )

        page_products = parse_products_from_html(
            html=html,
            category=category,
            term=term,
            source_url=url,
            page=page,
        )

        print(
            f"  Productos página {page}: "
            f"{len(page_products)}"
        )

        all_products.extend(
            page_products
        )

    print(
        f"  Productos encontrados "
        f"Super Food total: "
        f"{len(all_products)}"
    )

    return all_products


def export_lmstudio(df):

    txt_path = (
        LM_DIR /
        f"superfood_aruba_products_rag_"
        f"{TIMESTAMP}.txt"
    )

    csv_path = (
        LM_DIR /
        f"superfood_aruba_master_clean_"
        f"{TIMESTAMP}.csv"
    )

    jsonl_path = (
        LM_DIR /
        f"superfood_aruba_products_rag_"
        f"{TIMESTAMP}.jsonl"
    )

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    with open(
        txt_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "SUPER FOOD ARUBA "
            "RETAIL INTELLIGENCE DATABASE\n\n"
        )

        for idx, r in df.iterrows():

            f.write(f"PRODUCT {idx + 1}\n")

            for col in df.columns:

                f.write(
                    f"{col}: "
                    f"{r.get(col, '')}\n"
                )

            f.write("---\n\n")

    with open(
        jsonl_path,
        "w",
        encoding="utf-8"
    ) as f:

        for _, r in df.iterrows():

            f.write(
                r.to_json(force_ascii=False)
                + "\n"
            )

    return (
        csv_path,
        txt_path,
        jsonl_path
    )


def main():

    all_products = []

    driver = None

    try:
        driver = start_driver()

        if driver is None:
            print("Chrome no pudo iniciar.")
            return

        for category, terms in SEARCH_TERMS.items():

            for term in terms:

                try:
                    products = scrape_search(
                        driver,
                        category,
                        term,
                    )

                    all_products.extend(products)

                except Exception as e:
                    print(f"ERROR EN {category} | {term}: {e}")

                    try:
                        driver.quit()
                    except Exception:
                        pass

                    print("Reiniciando Chrome...")
                    driver = start_driver()

                time.sleep(5)

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

    df = pd.DataFrame(all_products)

    if df.empty:
        print("No se encontraron productos.")
        return
    df = df.drop_duplicates()

    output_file = (
        OUTPUT_DIR /
        f"superfood_aruba_retail_intelligence_{TIMESTAMP}.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    lm_csv, lm_txt, lm_jsonl = export_lmstudio(df)

    print("\n===================================")
    print(" SUPER FOOD ARUBA FINISHED")
    print("===================================")

    print(f"Productos totales: {len(df)}")
    print(f"CSV: {output_file}")
    print(f"LM CSV: {lm_csv}")
    print(f"LM TXT: {lm_txt}")
    print(f"LM JSONL: {lm_jsonl}")

if __name__ == "__main__":
    main()
