"""
CARIBBEAN RETAIL INTELLIGENCE AI
MASTER PIPELINE - FINAL VERSION
"""

import re
import subprocess
import pandas as pd
import numpy as np
import shutil

from pathlib import Path
from datetime import datetime

from brand_dictionary import infer_brand as infer_brand_from_dictionary
from product_dictionary import infer_product_from_dictionary

FORCE_SCRAPE = False
# ======================================================
# PATHS
# ======================================================

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")

OUTPUT_RD = BASE_DIR / "outputs/rd"
OUTPUT_GUYANA = BASE_DIR / "outputs/guyana/lmstudio"
OUTPUT_ARUBA = BASE_DIR / "outputs/aruba"

REGIONAL_OUTPUT = BASE_DIR / "outputs/regional"
REGIONAL_OUTPUT.mkdir(parents=True, exist_ok=True)

LM_OUTPUT = BASE_DIR / "lmstudio"
LM_OUTPUT.mkdir(parents=True, exist_ok=True)

# ======================================================
# STREAMLIT CLOUD
# ======================================================

STREAMLIT_DATA = BASE_DIR / "streamlit_data"
STREAMLIT_DATA.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")


# ======================================================
# UTILS
# ======================================================

def clean_text(x):

    if pd.isna(x):
        return pd.NA

    x = str(x).strip()

    if x.lower() in [
        "nan",
        "none",
        "null",
        ""
    ]:
        return pd.NA

    return x


def parse_number(x):

    if pd.isna(x):
        return np.nan

    x = str(x)

    x = (
        x.replace("$", "")
        .replace("RD", "")
        .replace("GYD", "")
        .replace("AWG", "")
        .replace(",", "")
        .strip()
    )

    match = re.search(
        r"\d+(?:\.\d+)?",
        x
    )

    if not match:
        return np.nan

    return float(match.group())


def extract_weight_kg(text):

    if pd.isna(text):
        return np.nan

    text = str(text).lower().replace(",", ".")

    kg_match = re.search(
        r"(\d+(?:\.\d+)?)\s?kg",
        text
    )

    if kg_match:
        return float(kg_match.group(1))

    g_match = re.search(
        r"(\d+(?:\.\d+)?)\s?g\b",
        text
    )

    if g_match:
        return float(g_match.group(1)) / 1000

    oz_match = re.search(
        r"(\d+(?:\.\d+)?)\s?oz",
        text
    )

    if oz_match:
        oz = float(oz_match.group(1))

        if oz > 100:
            oz = oz / 100

        return oz * 0.0283495

    lb_match = re.search(
        r"(\d+(?:\.\d+)?)\s?(lb|lbs|pound|pounds)",
        text
    )

    if lb_match:
        return float(lb_match.group(1)) * 0.453592

    return np.nan

def extract_unit_count(text):

    if pd.isna(text):
        return np.nan

    text = str(text).lower()

    patterns = [
        r"(\d+)\s?(und|unidad|unidades)",
        r"(\d+)\s?(ct|count)",
        r"(\d+)\s?(pack|paq)",
        r"pack\s?of\s?(\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            try:
                return int(
                    match.group(1)
                )
            except:
                pass

    return np.nan


def unit_bucket(x):

    try:
        x = int(x)

    except Exception:
        return "single"

    if x <= 2:
        return "single"

    elif x <= 8:
        return "smallpack"

    elif x <= 20:
        return "multipack"

    return "bulkpack"


def clean_brand(x):

    x = clean_text(x)

    if pd.isna(x):
        return pd.NA

    return str(x).strip().title()

def normalize_barcode_12(x):
    if pd.isna(x):
        return pd.NA

    x = str(x).strip().replace(".0", "")
    x = "".join(c for c in x if c.isdigit())

    if len(x) == 13:
        x = x[:12]
    elif len(x) != 12:
        return pd.NA

    bad_prefixes = ("210000", "205000", "151515", "999999")

    if x.startswith(bad_prefixes):
        return pd.NA

    return x

def infer_brand(row):

    brand = clean_brand(row.get("brand", pd.NA))

    invalid_brands = [
        "1/2", "2s", "17s", "25s", "6", "7", '7"',
        "8", '8"', "10", "12", "24", "36",
        "sale", "price", "remove", "from", "list",
        "items", "filters", "per", "page",
        "unknown", "nan", "none","other","unknown","galleta",
        "galletas", "pan","cookies","cookie","cracker",
        "crackers","bakery","snack","snacks","tortilla",
        "tortillas","de", "lu", "la","Bizcocho","cake","cupcake",
        "brownie","muffin","wrap","pan","wraps","tortilla",
        "tortillas","chips","snack","snacks","popcorn","mezcla",
        "ct","pc","ml","rm","st","ea","pk","bg","lb","oz","kg"
    ]

    if pd.notna(brand):
        b = str(brand).strip().lower()

        if (
            b not in invalid_brands
            and not re.match(r"^[0-9/\"'\-]+s?$", b)
            and len(b) > 1
        ):
            return brand

    product = clean_text(row.get("product_name", pd.NA))

    if pd.isna(product):
        return "Unknown"
    
    dictionary_brand = infer_brand_from_dictionary(product)

    if dictionary_brand and str(dictionary_brand).lower() not in ["other", "unknown"]:
        return dictionary_brand

    return "Unknown"   

def detect_segment(name):

    name = str(name).lower()

    premium_keywords = [
        "premium",
        "artisan",
        "organic",
        "gluten free",
        "whole grain",
        "multigrain",
        "gourmet",
        "protein",
        "natural",
    ]

    value_keywords = [
        "value",
        "economy",
        "basic",
        "family pack",
        "mega",
        "jumbo",
    ]

    if any(k in name for k in premium_keywords):
        return "Premium"

    if any(k in name for k in value_keywords):
        return "Value"

    return "Mass"
    
def clean_product_name(
    name,
    brand=None
):

    if pd.isna(name):
        return None

    clean = str(name)

    # =========================
    # LOWER
    # =========================

    clean = clean.lower()

    # =========================
    # REMOVE CURRENCY / PRICES
    # =========================

    clean = re.sub(
        r"(rd\$|usd|\$|ƒ|€)\s?\d+([.,]\d+)?",
        "",
        clean,
        flags=re.IGNORECASE
    )

    # =========================
    # REMOVE WEIGHTS
    # =========================

    clean = re.sub(
        r"\b\d+([.,]\d+)?\s?(oz|lb|lbs|g|gr|kg|ml|l|ea|pack|ct)\b",
        "",
        clean,
        flags=re.IGNORECASE
    )

    # =========================
    # REMOVE PACK EXPRESSIONS
    # =========================

    clean = re.sub(
        r"\b\d+\s?(paq|pack|und|unidades|count|ct)\b",
        "",
        clean,
        flags=re.IGNORECASE
    )

    # =========================
    # REMOVE SYMBOLS
    # =========================

    clean = re.sub(
        r"[\|\-,;/()]",
        " ",
        clean
    )

    # =========================
    # REMOVE BRAND
    # =========================

    if brand and brand != "Other":

        clean = re.sub(
            rf"\b{re.escape(str(brand).lower())}\b",
            "",
            clean,
            flags=re.IGNORECASE
        )

    # =========================
    # REMOVE EXTRA SPACES
    # =========================

    clean = re.sub(
        r"\s+",
        " ",
        clean
    ).strip()

    return clean.title()

def harmonize_product_name(name, brand=None):

    if pd.isna(name):
        return "unknown"
    
    dictionary_product = infer_product_from_dictionary(name)

    if dictionary_product:
        return dictionary_product
    
    x = str(name).lower()

    if brand and pd.notna(brand):
        x = re.sub(
            rf"\b{re.escape(str(brand).lower())}\b",
            "",
            x
        )

    replacements = {
        "cookies and cream": "cookies cream",
        "cookies & cream": "cookies cream",
        "choc chip": "chocolate chip",
        "choco chip": "chocolate chip",
        "sour cream & onion": "sour cream onion",
        "sour cream and onion": "sour cream onion",
        "s cream onion": "sour cream onion",
        "waffer": "wafer",
        "vainilla": "vanilla",
        "limon": "lemon",
        "limón": "lemon",
        "chocolate": "chocolate",
        "original": "original",
    }

    for old, new in replacements.items():
        x = x.replace(old, new)

    x = re.sub(
        r"\b\d+([.,]\d+)?\s?(oz|lb|lbs|g|gr|kg|ml|l|ea|pack|ct|und|unidades)\b",
        "",
        x
    )

    x = re.sub(
        r"[^a-z0-9\s]",
        " ",
        x
    )

    stopwords = {
        "galleta", "galletas", "cookie", "cookies",
        "cracker", "crackers", "pan", "bread",
        "tortilla", "tortillas", "wrap", "wraps",
        "sabor", "de", "del", "la", "el", "con",
        "and", "with", "the", "para",
        "sandwich", "rellena", "relleno",
        "pack", "paq", "und", "unidad", "unidades",
        "mini", "regular", "classic", "clasica", "clasico",
    }

    tokens = [
        t
        for t in x.split()
        if len(t) >= 3 and t not in stopwords
    ]

    tokens = sorted(set(tokens))

    if not tokens:
        return "unknown"

    return "_".join(tokens[:5]) 

def standardize_category(value):

    if pd.isna(value):
        return pd.NA

    v = str(value).lower().strip()

    if any(
        k in v
        for k in [
            "cookie",
            "galleta",
            "wafer",
            "biscuit"
        ]
    ):
        return "Cookies"

    if "cracker" in v:
        return "Crackers"

    if any(
        k in v
        for k in [
            "bread",
            "bakery",
            "bun",
            "roll",
            "panaderia",
        ]
    ):
        return "Bakery"

    if any(
        k in v
        for k in [
            "tortilla",
            "wrap"
        ]
    ):
        return "Tortillas & Wraps"

    if any(
        k in v
        for k in [
            "snack",
            "chips",
            "pretzel",
            "popcorn",
        ]
    ):
        return "Snacks"

    return str(value).title()
def classify_commercial_category(row):

    name = str(row.get("product_name", "")).lower()
    category = str(row.get("standard_category", "")).lower()
    family = str(row.get("commercial_family_key", "")).lower()

    text = f"{name} {category} {family}"

    if any(k in text for k in [
        "tortilla", "tortillas", "wrap", "wraps",
        "burrito", "taco", "tex mex", "old el paso"
    ]):
        return "TORTILLAS_WRAPS"

    if any(k in text for k in [
        "pita", "flatbread", "naan", "lavash"
    ]):
        return "PITA_FLATBREAD"

    if any(k in text for k in [
        "toast", "tostada", "tostadas", "pan tostado",
        "melba"
    ]):
        return "TOASTED_BREAD"

    if any(k in text for k in [
        "bagel", "bagels"
    ]):
        return "BAGELS"

    if any(k in text for k in [
        "hamburguesa", "hamburger", "burger buns",
        "hamburger_buns"
    ]):
        return "HAMBURGER_BUNS"

    if any(k in text for k in [
        "hot dog", "hotdog", "frank bun", "hotdog_buns"
    ]):
        return "HOTDOG_BUNS"
    # =========================
    # CRACKERS / SAVORY COOKIES
    # Must go before "integral" bread rules
    # =========================

    if any(k in text for k in [
        "club social",
        "soda_cracker",
        "saltina_cracker",
        "galleta de soda",
        "galletas de soda",
        "soda integral",
        "saltina",
        "saladitas",
        "cracker",
        "crackers",
        "ritz",
    ]):
        return "SAVORY_CRACKERS"
        # =========================
    # SWEET COOKIES
    # Must go before "integral" bread rules
    # =========================

    if any(k in text for k in [
        "galleta integral",
        "galletas integrales",
        "bisco pan galleta",
        "doraditas integral",
        "gullon vitalday",
        "gullon",
        "cookie",
        "cookies",
        "oreo",
        "chokis",
        "chips ahoy",
        "festival",
        "emperador",
        "mamut",
    ]):
        return "SWEET_COOKIES"
    
    if any(k in text for k in [
        "integral", "whole wheat", "wholewheat",
        "whole grain"
    ]):
        return "WHOLE_WHEAT_BREAD"

    if any(k in text for k in [
        "multigrano", "multigrain", "multicereal",
        "7 cereales", "avena", "oat", "fibra",
        "semillas", "ajonjoli", "ajonjolí"
    ]):
        return "SPECIALTY_BREAD"

    if any(k in text for k in [
        "pan blanco", "white bread", "sandwich blanco",
        "viga blanco", "blanco familiar"
    ]):
        return "WHITE_BREAD"
    
    if any(k in text for k in [
        "soda", "saltina", "cracker", "crackers",
        "ritz", "club social", "saladitas"
    ]):
        return "SAVORY_CRACKERS"    
    
    if any(k in text for k in [
        "oreo", "chokis", "chips ahoy", "festival",
        "emperador", "galleta", "galletas", "cookie",
        "cookies", "mamut"
    ]):
        return "SWEET_COOKIES"
    if any(k in text for k in [
        "wafer", "waffer", "barquillo"
    ]):
        return "WAFERS"


    if any(k in text for k in [
        "pringles", "doritos", "tostitos", "cheetos",
        "takis", "chips", "snack", "popcorn"
    ]):
        return "SALTY_SNACKS"

    if any(k in text for k in [
        "croissant", "muffin", "brownie", "bizcocho",
        "cake", "cupcake", "ponque", "ponqué"
    ]):
        return "SWEET_BAKERY"

    return "OTHER"

def harmonize_barcode(barcode):

    if pd.isna(barcode):
        return pd.NA

    barcode = str(barcode).strip().replace(".0", "")

    if not barcode.isdigit():
        return pd.NA

    # Filtrar códigos internos/sospechosos
    bad_prefixes = [
        "999999",
        "1779",
        "2000",
        "2500",
        "2600",
    ]

    if any(barcode.startswith(p) for p in bad_prefixes):
        return pd.NA

    # UPC12 -> EAN13
    if len(barcode) == 12:
        return barcode.zfill(13)

    # GTIN14 -> EAN13
    if len(barcode) == 14:

        if (
            barcode.startswith("0")
            or barcode.startswith("1")
        ):
            return barcode[1:]

        return barcode[-13:]

    # EAN13
    if len(barcode) == 13:
        return barcode

    return pd.NA

def build_family_key(row):

    barcode = str(
        row.get("barcode", "")
    ).strip()

    if barcode and barcode.lower() != "nan":

        barcode = re.sub(
            r"[^0-9]",
            "",
            barcode
        )

        if len(barcode) >= 8:
            return f"BC_{barcode}"

    brand = str(
        row.get("brand", "")
    ).upper().strip()

    name = str(
        row.get("product_name", "")
    ).upper()

    name = re.sub(
        r"[^A-Z0-9 ]",
        " ",
        name
    )

    STOP_WORDS = {
        "BREAD",
        "COOKIE",
        "COOKIES",
        "CRACKER",
        "CRACKERS",
        "CHIPS",
        "SNACK",
        "SNACKS",
        "BAGEL",
        "WRAP",
        "WRAPS",
        "TORTILLA",
        "TORTILLAS",
        "THE",
        "AND",
        "WITH",
        "OF",
    }

    tokens = [
        t
        for t in name.split()
        if (
            len(t) > 2
            and t not in STOP_WORDS
        )
    ]

    descriptor = "_".join(
        tokens[:5]
    )

    weight = row.get("weight_kg")

    if pd.notna(weight):
        weight_g = round(
            weight * 1000
        )
    else:
        weight_g = ""

    return (
        f"{brand}_{descriptor}_{weight_g}"
    )
# ======================================================
# RUN SCRAPERS
# ======================================================

def run_script(script_path, name):


    print("\n===================================")
    print(f" RUNNING {name}")
    print("===================================\n")

    if not script_path.exists():
        print(f"WARNING: scraper not found: {script_path}")
        return

    try:

        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=False,
            text=True
        )

        if result.returncode != 0:
            print(f"WARNING: {name} terminó con errores")

    except Exception as e:

        print(f"ERROR ejecutando {name}: {e}")

def has_today_file(folder, pattern="*.csv"):

    today = datetime.now().strftime("%Y%m%d")

    files = list(Path(folder).glob(pattern))

    for file in files:

        if today in file.name:
            return True

    return False

def latest_csv(folder):

    if not folder.exists():
        return None

    # Primero buscar archivos latest
    latest_files = sorted(
        folder.glob("*latest*.csv")
    )

    if latest_files:
        return latest_files[-1]

    files = [
        f for f in folder.glob("*.csv")
        if (
            "master" in f.name.lower()
            or "intelligence" in f.name.lower()
            or "clean" in f.name.lower()
        )
    ]

    if not files:
        return None

    return max(
        files,
        key=lambda x: x.stat().st_mtime
    )

# ======================================================
# LOAD CSV
# ======================================================

def safe_load_csv(path, country):

    try:

        print(f"Loading {country}: {path}")

        df = pd.read_csv(path)

        df.columns = [
            str(c).strip().lower()
            for c in df.columns
        ]

        df = df.replace(
            [
                "nan",
                "NaN",
                "None",
                "none",
                "NULL",
                "null",
                ""
            ],
            pd.NA
        )

        df = df.loc[
            :,
            ~df.columns.duplicated()
        ]

        def copy_if_empty(target, sources):

            for source in sources:

                if source in df.columns:

                    if target not in df.columns:

                        df[target] = df[source]

                    else:

                        df[target] = (
                            df[target]
                            .fillna(df[source])
                        )

                    break

        copy_if_empty(
            "category",
            [
                "categoria",
                "categoría",
                "source_category",
                "category"
            ]
        )

        copy_if_empty(
            "brand",
            ["marca", "brand"]
        )

        copy_if_empty(
            "product_name",
            [
                "producto",
                "product",
                "nombre",
                "product_name"
            ]
        )

        copy_if_empty(
            "retailer",
            [
                "retailer",
                "cadena",
                "supermercado"
            ]
        )

        copy_if_empty(
            "price_local",
            [
                "precio",
                "price",
                "price_local"
            ]
        )

        copy_if_empty(
            "presentation",
            [
                "presentación",
                "presentation",
                "size"
            ]
        )

        copy_if_empty(
            "weight_kg",
            [
                "weight_kg",
                "peso_kg"
            ]
        )

        copy_if_empty(
            "price_usd",
            [
                "price_usd",
                "precio_usd"
            ]
        )

        copy_if_empty(
            "price_per_kg_usd",
            [
                "price_per_kg_usd",
                "precio_kg_usd"
            ]
        )

        copy_if_empty(
            "barcode",
            [
                "barcode",
                "upc",
                "ean",
                "gtin"
            ]
        )

        # Ensure required columns exist
        required_cols = [
            "category",
            "brand",
            "product_name",
            "retailer",
            "presentation",
            "price_local",
            "price_usd",
            "price_per_kg_usd",
            "weight_kg",
            "unit_count",
            "barcode",
            "barcode_length",
        ]

        for col in required_cols:
            if col not in df.columns:
                df[col] = pd.NA

        if "country" not in df.columns:
            df["country"] = country

        # =========================
        # CLEAN PRODUCT NAME
        # =========================

        df["product_name_clean"] = df.apply(
            lambda x: clean_product_name(
                x["product_name"],
                x["brand"]
            ),
            axis=1
        )

        # =========================
        # CLEAN TEXT
        # =========================

        for col in [
            "category",
            "brand",
            "product_name",
            "retailer",
            "presentation",
        ]:

            if col in df.columns:

                df[col] = df[col].apply(
                    clean_text
                )

        # =========================
        # CATEGORY
        # =========================

        df["standard_category"] = (
            df["category"]
            .apply(standardize_category)
        )

        # =========================
        # BRAND
        # =========================

        df["brand"] = df.apply(
            infer_brand,
            axis=1
        )

        # =========================
        # WEIGHT
        # =========================

        df["weight_kg"] = pd.to_numeric(
            df["weight_kg"],
            errors="coerce"
        )

        inferred_weight = (
            df["presentation"]
            .apply(extract_weight_kg)
        )

        inferred_weight_2 = (
            df["product_name"]
            .apply(extract_weight_kg)
        )

        df["weight_kg"] = (
            df["weight_kg"]
            .fillna(inferred_weight)
            .fillna(inferred_weight_2)
        )

        # =========================
        # UNIT COUNT
        # =========================

        df["unit_count"] = (
            df["product_name"]
            .apply(extract_unit_count)
        )

        df["unit_count"] = (
            df["unit_count"]
            .fillna(
                df["presentation"]
                .apply(extract_unit_count)
            )
        )

        # =========================
        # PRICES
        # =========================

        df["price_local_numeric"] = (
            df["price_local"]
            .apply(parse_number)
        )

        df["price_usd"] = pd.to_numeric(
            df["price_usd"],
            errors="coerce"
        )

        df["price_per_kg_usd"] = pd.to_numeric(
            df["price_per_kg_usd"],
            errors="coerce"
        )

        df.loc[
            (df["price_usd"].notna())
            & (df["weight_kg"].notna())
            & (df["weight_kg"] > 0),
            "price_per_kg_usd"
        ] = (
            df["price_usd"]
            / df["weight_kg"]
        )

        # =========================
        # BARCODE NORMALIZATION
        # =========================

        if "barcode" in df.columns:

            df["barcode"] = (
                df["barcode"]
                .astype("string")
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

            df.loc[
                ~df["barcode"].str.match(
                    r"^\d{12,14}$",
                    na=False
                ),
                "barcode"
            ] = pd.NA

            df["barcode_length"] = (
                df["barcode"]
                .astype("string")
                .str.len()
            )

        else:

            df["barcode"] = pd.NA
            df["barcode_length"] = pd.NA

        # =========================
        # SEGMENT
        # =========================

        df["segment"] = (
            df["product_name"]
            .apply(detect_segment)
        )
        # =========================
        # REMOVE FAKE CATEGORY ROWS
        # =========================

        FAKE_PRODUCTS = {
            "other",
            "bakery",
            "cookies",
            "null",
            "brandy/cognac",
            "non alcoholic wine",
            "gift cards",
            "phone cards - pin top up",
            "pharmacy",
            "pharmaceutical",
            "personal care",
            "paper products",
            "packaging supplies other",
            "paint",
            "pain relief",
            "oxtails",
            "parboiled rice",
            "pasta",
            "penne",
        }

        before_rows = len(df)

        df = df[
            ~df["product_name"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(FAKE_PRODUCTS)
        ].copy()

        removed_rows = before_rows - len(df)

        if removed_rows > 0:
            print(f"Removed fake/category rows {country}: {removed_rows}")

        print(f"Rows loaded {country}: {len(df)}")

        return df

    except Exception as e:

        print(f"ERROR loading {path}: {e}")

        return pd.DataFrame()


# ======================================================
# BUILD REGIONAL DATASET
# ======================================================

def build_regional_dataset():

    datasets = []

    sources = [
        ("Dominican Republic", OUTPUT_RD),
        ("Guyana", OUTPUT_GUYANA),
        ("Aruba", OUTPUT_ARUBA),
    ]

    for country, folder in sources:

        csv_file = latest_csv(folder)

        if csv_file:

            df_country = safe_load_csv(
                csv_file,
                country
            )

            if not df_country.empty:
                datasets.append(df_country)

        else:

            print(
                f"WARNING: no CSV found for "
                f"{country}"
            )

    if not datasets:
        return pd.DataFrame(), pd.DataFrame()

    regional_df = pd.concat(
        datasets,
        ignore_index=True,
        sort=False
    )
    # ==========================================
    # BRAND CORRECTIONS
    # ==========================================

    try:

        corrections = pd.read_excel(
            "brand_corrections.xlsx"
        )

        corrections.columns = [
            c.strip()
            for c in corrections.columns
        ]

        regional_df["product_name"] = (
            regional_df["product_name"]
            .astype(str)
            .str.strip()
        )

        corrections["product_name"] = (
            corrections["product_name"]
            .astype(str)
            .str.strip()
        )

        regional_df["brand_original"] = (
            regional_df["brand"]
        )

        regional_df = regional_df.merge(
            corrections[["product_name", "Marca"]],
            on="product_name",
            how="left"
        )

        regional_df["brand"] = (
            regional_df["Marca"]
            .fillna(regional_df["brand"])
            .astype(str)
            .str.strip()
        )

        regional_df.drop(
            columns=["Marca"],
            inplace=True
        )

        print("Brand corrections applied.")

    except Exception as e:

        print(f"Brand correction error: {e}")
    except Exception as e:

        print(f"Brand correction error: {e}")

    # ==========================================
    # BRAND GROUP NORMALIZATION
    # Parent company / brand family
    # ==========================================

    def normalize_brand_group(brand):

        if pd.isna(brand):
            return "Unknown"

        b = str(brand).strip().lower()

        BRAND_GROUPS = {
            # PEPSICO / FRITO-LAY
            "lays": "PepsiCo / Frito-Lay",
            "lay's": "PepsiCo / Frito-Lay",
            "fritolay": "PepsiCo / Frito-Lay",
            "frito lay": "PepsiCo / Frito-Lay",
            "doritos": "PepsiCo / Frito-Lay",
            "cheetos": "PepsiCo / Frito-Lay",
            "tostitos": "PepsiCo / Frito-Lay",
            "ruffles": "PepsiCo / Frito-Lay",
            "sun chips": "PepsiCo / Frito-Lay",

            # MONDELEZ
            "oreo": "Mondelez",
            "ritz": "Mondelez",
            "chips ahoy": "Mondelez",
            "belvita": "Mondelez",
            "triscuit": "Mondelez",
            "nabisco": "Mondelez",

            # GRUPO BIMBO
            "bimbo": "Grupo Bimbo",
            "tia rosa": "Grupo Bimbo",
            "tía rosa": "Grupo Bimbo",
            "sanissimo": "Grupo Bimbo",
            "saníssimo": "Grupo Bimbo",
            "takis": "Grupo Bimbo",

            # BAUDUCCO
            "bauducco": "Bauducco",

            # KELLANOVA
            "pringles": "Kellanova",
            "kellogg": "Kellanova",
            "cheez-it": "Kellanova",

            # CAMPBELL'S
            "pepperidge farm": "Campbell's",
            "goldfish": "Campbell's",

            # GRUMA
            "mission": "Gruma",
            "guerrero": "Gruma",
            "maseca": "Gruma",

            # TORTILLAS / BAKERY
            "toufayan": "Toufayan",

            # OTHERS
            "colombina": "Colombina",
            "planters": "Hormel / Planters",
            "snickers": "Mars",
            "m&m": "Mars",
            "m&ms": "Mars",
            "walkers": "Walkers",
            "mcvitie": "McVitie's",
            "mcvities": "McVitie's",
            "reynolds": "Reynolds",
            "glad": "Glad"
        }

        return BRAND_GROUPS.get(
            b,
            str(brand).strip()
        )

    regional_df["brand_group"] = (
        regional_df["brand"]
        .apply(normalize_brand_group)
    )

    print("Brand groups normalized.")
       # ==========================================
    # BRAND NORMALIZATION ENGINE
    # Missing brands backlog
    # ==========================================

    try:

        missing_brands = regional_df[
            regional_df["brand"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["other", "unknown", "nan", "none"])
        ].copy()

        if not missing_brands.empty:

            missing_brands["dictionary_brand"] = (
                missing_brands["product_name"]
                .apply(lambda x: infer_brand({"product_name": x}))
            )

            missing_brands = missing_brands[
                missing_brands["dictionary_brand"]
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("other")
            ]

            def extract_possible_brand(name):

                if pd.isna(name):
                    return "Unknown"

                words = (
                    str(name)
                    .replace("-", " ")
                    .strip()
                    .split()
                )

                if not words:
                    return "Unknown"

                two_word_brands = {
                    "Hungry Jack",
                    "Mc Cain",
                    "Bet Crock",
                    "Food For",
                    "Golden Harvest",
                    "Morning Star",
                    "Betty Crocker",
                    "Two Bite",
                    "Bobs Red",
                }

                candidate_2 = (
                    " ".join(words[:2])
                    .title()
                )

                if candidate_2 in two_word_brands:
                    return candidate_2

                return words[0].title()


            missing_brands["possible_brand"] = (
                missing_brands["product_name"]
                .apply(extract_possible_brand)
            )

            GENERIC_BRANDS = {
                "Other", "Unknown",
                "Pan", "Bread", "Bakery", "Frozen",
                "Galleta", "Galletas", "Cookie", "Cookies",
                "Cracker", "Crackers", "Wafer",
                "Bizcocho", "Cake", "Cupcake", "Brownie",
                "Muffin", "Muffins", "Mini",
                "Pita", "Wrap", "Wraps",
                "Tortilla", "Tortillas",
                "Chips", "Snack", "Snacks",
                "Mezcla", "Barra", "Helado", "Helados",
                "Croissant", "Flatbread", "Viga",
                "Sweet", "Grocery", "Wrapping",
                "Molde", "Capacillos", "Leche",
                "Paleta", "Milk", "Meat", "Soft",
                "Each", "Flavoured", "Plastico",
                "Ft", "Mc", "Bet", "Nv", "Hungry", "Food",
            }
            GENERIC_BRANDS.update({
                "Topper",
                "Hamburguesa",
                "Papel",
                "Hilo",
                "Servilletas",
                "Papas",
                "Pavo",
                "Filete",
                "Baguette",
                "Casabe",
                "Cheesecake",
                "Cereal",
                "Dulce",
                "Palmeras",
                "Variety",
            })
            missing_summary = (
                missing_brands
                .groupby(
                    [
                        "possible_brand",
                        "country",
                        "source_category",
                        "search_term",
                    ],
                    dropna=False
                )
                .agg(
                    records=("product_name", "count"),
                    sample_product=("product_name", "first"),
                )
                .reset_index()
                .sort_values(
                    "records",
                    ascending=False
                )
            )

            missing_summary = missing_summary[
                ~missing_summary["possible_brand"]
                .isin(GENERIC_BRANDS)
            ]

            missing_file = (
                REGIONAL_OUTPUT /
                f"missing_brand_backlog_{TIMESTAMP}.csv"
            )

            missing_summary.to_csv(
                missing_file,
                index=False,
                encoding="utf-8-sig"
            )

            print("\n===================================")
            print(" BRAND NORMALIZATION ENGINE")
            print("===================================")
            print("Missing brand candidates:")
            print(missing_summary.head(50))
            print(f"Backlog file: {missing_file}")

        else:

            print("No missing brands found.")

    except Exception as e:

        print(f"Brand normalization engine error: {e}")

    # ==================================================
    # SKU TEXT NORMALIZATION
    # ==================================================
    
    def normalize_sku_text(x):
    
        if pd.isna(x):
            return ""
    
        x = str(x).lower()
    
        x = re.sub(
            r"[^a-z0-9\s]",
            " ",
            x
        )
    
        x = re.sub(
            r"\s+",
            " ",
            x
        ).strip()
    
        stopwords = [
            "sale",
            "price",
            "remove",
            "from",
            "list",
            "gluten",
            "free",
            "pack",
            "ct",
            "oz",
            "gram",
            "grams",
            "g",
            "kg",
        ]
    
        for w in stopwords:
    
            x = re.sub(
                rf"\b{w}\b",
                "",
                x
            )
    
        return re.sub(
            r"\s+",
            " ",
            x
        ).strip()
    
    
    # ==================================================
    # SKU TEXT KEY
    # ==================================================
    
    regional_df["sku_text_key"] = (
        regional_df["brand"]
        .astype(str)
        .apply(normalize_sku_text)
        + "_"
        +
        regional_df["product_name"]
        .astype(str)
        .apply(normalize_sku_text)
    )
    
    # ==================================================
    # WEIGHT BUCKET
    # ==================================================
    
    regional_df["weight_bucket"] = (
        regional_df["weight_kg"]
        .round(2)
        .astype("string")
        .fillna("unknown")
    )
    regional_df["unit_bucket"] = (
        regional_df["unit_count"]
        .apply(unit_bucket)
    )
    # ==================================================
    # MATCH KEY
    # ==================================================
    
    regional_df["match_key"] = (
        regional_df["sku_text_key"]
        + "_"
        + regional_df["weight_bucket"]
    )

    regional_df["match_key"] = (
        pd.Series(regional_df["match_key"])
        .astype("string")
        .fillna(
            regional_df["sku_text_key"].astype("string")
            + "_unknown"
        )
    )

    # ==================================================
    # BARCODE HARMONIZATION
    # ==================================================

    if "barcode" not in regional_df.columns:
        regional_df["barcode"] = pd.NA

    regional_df["barcode_raw"] = regional_df["barcode"]

    regional_df["barcode_12"] = (
        regional_df["barcode"]
        .apply(normalize_barcode_12)
    )

    regional_df["barcode_harmonized"] = (
        regional_df["barcode_12"]
    )
        # ==========================================
    # FAKE / REUSED BARCODES BLACKLIST
    # ==========================================

    FAKE_BARCODES = {
        "753081009133",
        "255250000000",
        "254005000000",
        "810023430087",
        "254072000000",
        "254151000000",
    }

    regional_df.loc[
        regional_df["barcode_harmonized"]
        .astype(str)
        .isin(FAKE_BARCODES),
        "barcode_harmonized"
    ] = pd.NA
    # ==================================================
    # FAMILY MATCHING ENGINE
    # Commercial engine is calculated below
    # ==================================================

    print("\n===================================")
    print(" FAMILY MATCHING ENGINE")
    print("===================================")

    print("Using commercial_overlap engine.")

    # ==================================================
    # REGIONAL OVERLAP
    # ==================================================
    

    print("\nTop Match Keys")

    print(
        regional_df[
            regional_df["barcode_harmonized"].notna()
        ]
        .groupby("barcode_harmonized")
        .agg(
            countries=("country", "nunique"),
            rows=("country", "count"),
            product=("product_name", "first")
        )
        .sort_values(
            "countries",
            ascending=False
        )
        .head(20)
    )

    # ==================================================
    # PRODUCT NAME HARMONIZATION
    # ==================================================

    regional_df["product_name_harmonized"] = (
        regional_df.apply(
            lambda row: harmonize_product_name(
                row.get("product_name", ""),
                row.get("brand", "")
            ),
            axis=1
        )
    )

    # ==================================================
    # FAMILY KEY - FUZZY COMMERCIAL MATCH
    # ==================================================
    def family_key(row):

        brand = normalize_sku_text(
            row.get("brand", "")
        )

        product = str(
            row.get("product_name_harmonized", "unknown")
        ).strip()

        if not brand:
            brand = "unknown"

        if not product:
            product = "unknown"

        return f"{product}"

     
    # ==================================================
    # FAMILY KEYS
    # ==================================================

    regional_df["commercial_family_key"] = (
        regional_df.apply(
            family_key,
            axis=1
        )
    )

    regional_df["sku_family_key"] = (
        regional_df["brand"]
        .astype(str)
        .apply(normalize_sku_text)
        + "_"
        + regional_df["product_name_harmonized"]
        .astype(str)
    )

    regional_df["family_key"] = (
        regional_df["commercial_family_key"]
    )
        # ==================================================
    # BENCHMARK FAMILY KEY
    # More strict key for price gap analysis
    # ==================================================

    def benchmark_family_key(row):

        brand = normalize_sku_text(
            row.get("brand", "")
        )

        product = normalize_sku_text(
            row.get("product_name", "")
        )

        category = str(
            row.get("commercial_category", "")
        ).lower()

        if not brand:
            brand = "unknown"

        text = f"{brand} {product} {category}"

        # Ritz cleanup
        if "ritz" in text:

            if "spritz" in text or "spritzer" in text:
                return "exclude_from_benchmark"

            if "chips" in text or "crisp" in text or "thin" in text or "toasted" in text:
                return f"{brand}_ritz_chips"

            if "bits" in text:
                return f"{brand}_ritz_bits"

            if "sandwich" in text or "peanut" in text:
                return f"{brand}_ritz_sandwich"

            if "queso" in text or "cheese" in text or "cheddar" in text:
                return f"{brand}_ritz_cheese"

            return f"{brand}_ritz_crackers"

        # Oreo cleanup
        if "oreo" in text:

            if "vanilla" in text or "vainilla" in text or "golden" in text:
                return f"{brand}_oreo_vanilla"

            if "chocolate" in text or "choco" in text:
                return f"{brand}_oreo_chocolate"

            if "thin" in text:
                return f"{brand}_oreo_thins"

            return f"{brand}_oreo_original"

        # Hot dog buns only, not meat hot dogs
        if category == "hotdog_buns":

            if any(x in product for x in [
                "gwaltney",
                "ball park",
                "beef",
                "chicken",
                "sausage",
                "meat",
                "angus"
            ]):
                return "exclude_from_benchmark"

            return f"{brand}_hotdog_buns"
        
        # Hamburger buns
        if category == "hamburger_buns":
            return f"{brand}_hamburger_buns"

        return f"{brand}_{row.get('commercial_family_key', 'unknown')}"
    
    regional_df["benchmark_family_key"] = (
    regional_df.apply(
        benchmark_family_key,
        axis=1
    )
)

    # ==================================================
    # COMMERCIAL CATEGORY
    # ==================================================

    regional_df["commercial_category"] = (
        regional_df.apply(
            classify_commercial_category,
            axis=1
        )
    )
    regional_df["commercial_overlap"] = (
        regional_df.groupby("commercial_family_key")["country"]
        .transform("nunique")
    )

    regional_df["sku_overlap"] = (
        regional_df.groupby("sku_family_key")["country"]
        .transform("nunique")
    )

    regional_df["regional_overlap"] = (
        regional_df["commercial_overlap"]
    )

    print("\nCommercial Overlap")

    print(
        regional_df["commercial_overlap"]
        .value_counts()
        .sort_index()
    )
    # ==================================================
    # SAME SKU PRICE GAP
    # ==================================================

    regional_price_gap = (
        regional_df[
            regional_df["commercial_overlap"] > 1
        ]
    .groupby(
        [
            "benchmark_family_key"
        ]
    )
        .agg(
            countries=("country", "nunique"),
            retailers=("retailer", "nunique"),
            min_price_per_kg_usd=("price_per_kg_usd", "min"),
            max_price_per_kg_usd=("price_per_kg_usd", "max"),
            avg_price_per_kg_usd=("price_per_kg_usd", "mean"),
            product_name=("product_name", "first"),
            presentations=("presentation", "nunique"),
        )
        .reset_index()
            )

    regional_price_gap = (
        regional_df[
            (regional_df["commercial_overlap"] > 1)
            & (regional_df["price_per_kg_usd"].notna())
            & (regional_df["price_per_kg_usd"] > 0)
            & (regional_df["price_per_kg_usd"] >= 1)
            & (regional_df["price_per_kg_usd"] <= 80)
            & (~regional_df["product_name"].astype(str).str.contains(
                "gwaltney|ball park|beef hot dogs|chicken original bun size",
                case=False,
                na=False
            ))
            & (
                regional_df["benchmark_family_key"]
                != "exclude_from_benchmark"
            )
        ]
        .groupby("benchmark_family_key")
        .agg(
            brand=("brand", "first"),
            product_name=("product_name", "first"),
            countries=("country", "nunique"),
            retailers=("retailer", "nunique"),
            min_price_per_kg_usd=("price_per_kg_usd", "min"),
            max_price_per_kg_usd=("price_per_kg_usd", "max"),
            avg_price_per_kg_usd=("price_per_kg_usd", "mean"),
            presentations=("presentation", "nunique"),
        )
        .reset_index()
    )

    regional_price_gap["price_gap_per_kg_usd"] = (
        regional_price_gap["max_price_per_kg_usd"]
        - regional_price_gap["min_price_per_kg_usd"]
    )

    regional_price_gap["price_gap_pct"] = np.where(
        regional_price_gap["min_price_per_kg_usd"] > 0,
        (
            regional_price_gap["price_gap_per_kg_usd"]
            / regional_price_gap["min_price_per_kg_usd"]
        ) * 100,
        np.nan
    )

    regional_price_gap = regional_price_gap.sort_values(
        "price_gap_pct",
        ascending=False
    )
    # ==================================================
    # COMPETITIVE INDEX
    # ==================================================

    regional_df["competitive_index"] = (
        regional_df["price_per_kg_usd"]
        /
        regional_df.groupby(
            "standard_category"
        )["price_per_kg_usd"]
        .transform("mean")
    )

    regional_df["price_positioning"] = np.where(
        regional_df["competitive_index"] >= 1.20,
        "Premium",
        np.where(
            regional_df["competitive_index"] <= 0.80,
            "Value",
            "Market"
        )
    )

    # ==================================================
    # DEDUP
    # ==================================================

    regional_df = regional_df.drop_duplicates(
        subset=[
            "country",
            "retailer",
            "product_name",
            "price_usd",
            "barcode"
        ]
    )

    # ==================================================
    # LOGS
    # ==================================================

    print("\n===================================")
    print(" REGIONAL DATASET")
    print("===================================\n")

    print(f"Total regional SKUs: {len(regional_df)}")

    print(
        "\nBarcodes encontrados:",
        regional_df["barcode"]
        .notna()
        .sum()
    )

    print("\nOverlap regional:")

    print(
        regional_df["regional_overlap"]
        .value_counts()
        .sort_index()
    )

    print("\nTop SKU regional price gaps:")

    try:

        print(
            regional_price_gap[
                [
                    "brand",
                    "product_name",
                    "countries",
                    "min_price_per_kg_usd",
                    "max_price_per_kg_usd",
                    "price_gap_pct"
                ]
            ]
            .head(15)
        )

    except Exception as e:

        print(f"ERROR regional gaps: {e}")

    return regional_df, regional_price_gap


# ======================================================
# EXPORTS
# ======================================================

def export_regional_files(
    df,
    regional_price_gap
):

    if df.empty:
        print("Regional dataframe vacío.")
        return

    regional_excel = (
        REGIONAL_OUTPUT
        / f"caribbean_master_{TIMESTAMP}.xlsx"
    )

    regional_latest_excel = (
        REGIONAL_OUTPUT
        / "caribbean_master_latest.xlsx"
    )

    regional_csv = (
        REGIONAL_OUTPUT
        / f"caribbean_master_{TIMESTAMP}.csv"
    )

    regional_latest_csv = (
        REGIONAL_OUTPUT
        / "caribbean_master_latest.csv"
    )

    regional_txt = (
        LM_OUTPUT
        / f"caribbean_rag_{TIMESTAMP}.txt"
    )

    regional_jsonl = (
        LM_OUTPUT
        / f"caribbean_rag_{TIMESTAMP}.jsonl"
    )

    with pd.ExcelWriter(
        regional_latest_excel,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Regional Master",
            index=False
        )

        regional_price_gap.to_excel(
            writer,
            sheet_name="SKU Price Gaps",
            index=False
        )

    df.to_csv(
        regional_csv,
        index=False,
        encoding="utf-8-sig"
    )

    df.to_csv(
        regional_latest_csv,
        index=False,
        encoding="utf-8-sig"
    )

    with open(
        regional_txt,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "CARIBBEAN RETAIL "
            "INTELLIGENCE DATABASE\n\n"
        )

        for idx, row in df.iterrows():

            f.write(f"PRODUCT {idx+1}\n")

            for col in [
                "country",
                "retailer",
                "brand",
                "product_name",
                "price_usd",
                "price_per_kg_usd",
                "barcode",
            ]:

                f.write(
                    f"{col}: "
                    f"{row.get(col, '')}\n"
                )

            f.write("\n---\n\n")

    with open(
        regional_jsonl,
        "w",
        encoding="utf-8"
    ) as f:

        for _, row in df.iterrows():
            f.write(
                row.to_json(force_ascii=False)
                + "\n"
            )

    files_to_publish = [
        regional_latest_excel,
        regional_latest_csv,
        REGIONAL_OUTPUT / "alerts/price_alerts.xlsx",
        REGIONAL_OUTPUT / "insights/regional_insights.xlsx",
    ]

    for file in files_to_publish:
        if file.exists():
            shutil.copy2(
                file,
                STREAMLIT_DATA / file.name
            )            

    print("\n===================================")
    print(" REGIONAL FILES CREATED")
    print("===================================\n")

    print(f"Excel: {regional_excel}")
    print(f"CSV: {regional_csv}")
    print(f"TXT: {regional_txt}")
    print(f"JSONL: {regional_jsonl}")
    print(f"Latest Excel: {regional_latest_excel}")
    print(f"Latest CSV: {regional_latest_csv}")


# ======================================================
# MAIN
# ======================================================
def is_file_modified_today(file_path):

    file_path = Path(file_path)

    if not file_path.exists():
        return False

    file_date = datetime.fromtimestamp(
        file_path.stat().st_mtime
    ).strftime("%Y%m%d")

    today = datetime.now().strftime("%Y%m%d")

    return file_date == today
def main():

    print("\n===================================")
    print(" CARIBBEAN RETAIL INTELLIGENCE AI")
    print("===================================\n")

    # ==========================================
    # RD
    # ==========================================

    rd_master_file = OUTPUT_RD / "benchmark_rd_master.csv"

    if not FORCE_SCRAPE and is_file_modified_today(
        rd_master_file
    ):
        print("RD ya tiene archivo maestro actualizado hoy. Se omite scraper RD.")

    else:

        run_script(
            BASE_DIR / "scrapers/rd_retail_intelligence.py",
            "RD SCRAPER"
        )

    # ==========================================
    # GUYANA
    # ==========================================

    guyana_master_file = (
        OUTPUT_GUYANA /
        "guyana_master_clean_latest.csv"
    )

    if not FORCE_SCRAPE and is_file_modified_today(
        guyana_master_file
    ):
        print("Guyana ya tiene archivo maestro actualizado hoy. Se omite scraper Guyana.")

    else:

        run_script(
            BASE_DIR / "scrapers/guyana_retail_intelligence.py",
            "GUYANA SCRAPER"
        )

    # ==========================================
    # ARUBA
    # ==========================================

    aruba_master_file = (
        OUTPUT_ARUBA /
        "superfood_aruba_retail_intelligence_latest.csv"
    )

    if not FORCE_SCRAPE and is_file_modified_today(
        aruba_master_file
    ):
        print("Aruba ya tiene archivo maestro actualizado hoy. Se omite scraper Aruba.")

    else:

        run_script(
            BASE_DIR / "scrapers/superfood_aruba_intelligence.py",
            "ARUBA SCRAPER"
        )

    print("\n===================================")
    print(" CARIBBEAN RETAIL INTELLIGENCE AI")
    print("===================================\n")



    regional_df, regional_price_gap = (
        build_regional_dataset()
    )

    export_regional_files(
        regional_df,
        regional_price_gap
    )

    print("\n===================================")
    print(" PIPELINE FINISHED")
    print("===================================\n")



if __name__ == "__main__":
    main()