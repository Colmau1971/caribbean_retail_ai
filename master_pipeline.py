"""
CARIBBEAN RETAIL INTELLIGENCE AI
MASTER PIPELINE - FINAL VERSION
"""

import re
import subprocess
import pandas as pd
import numpy as np

from pathlib import Path
from datetime import datetime


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
        return float(oz_match.group(1)) * 0.0283495

    lb_match = re.search(
        r"(\d+(?:\.\d+)?)\s?(lb|lbs|pound|pounds)",
        text
    )

    if lb_match:
        return float(lb_match.group(1)) * 0.453592

    return np.nan


def clean_brand(x):

    x = clean_text(x)

    if pd.isna(x):
        return pd.NA

    return str(x).strip().title()


def infer_brand(row):

    brand = clean_brand(row.get("brand", pd.NA))

    invalid_brands = [
        "1/2", "2s", "17s", "25s", "6", "7", '7"',
        "8", '8"', "10", "12", "24", "36",
        "sale", "price", "remove", "from", "list",
        "items", "filters", "per", "page",
        "unknown", "nan", "none"
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

    words = str(product).split()

    for w in words:
        candidate = w.strip().title()
        c = candidate.lower()

        if (
            c not in invalid_brands
            and not re.match(r"^[0-9/\"'\-]+s?$", c)
            and len(c) > 1
        ):
            return candidate

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


def latest_csv(folder):

    if not folder.exists():
        return None

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

        if "weight_kg" not in df.columns:
            df["weight_kg"] = np.nan

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

        df["price_per_kg_usd"] = (
            df["price_per_kg_usd"]
            .fillna(
                df["price_usd"] /
                df["weight_kg"]
            )
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

        corrections = pd.read_csv(
            "brand_corrections.csv"
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

    # ==========================================
    # REMOVE "OTHER" BRANDS
    # ==========================================

    regional_df = regional_df[
        regional_df["brand"]
        .astype(str)
        .str.strip()
        .str.lower()
        != "other"
    ]

    print('Removed brand "Other".')
    
   
    regional_df.columns = [
        str(c).strip().lower()
        for c in regional_df.columns
    ]

    regional_df = regional_df.replace(
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

    regional_df = regional_df.loc[
        :,
        ~regional_df.columns.duplicated()
    ]

    # ==================================================
    # BARCODE HARMONIZATION
    # ==================================================

    regional_df["barcode_harmonized"] = (
        regional_df["barcode"]
        .apply(harmonize_barcode)
    )

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
    
    # ==================================================
    # MATCH KEY
    # ==================================================
    
    regional_df["match_key"] = np.where(
        regional_df["barcode_harmonized"].notna(),
        regional_df["barcode_harmonized"],
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
    # REGIONAL OVERLAP
    # ==================================================
    
    regional_df["regional_overlap"] = (
        regional_df.groupby("match_key")["country"]
        .transform("nunique")
    )
 
       # ==================================================
    # FAMILY KEY - FUZZY COMMERCIAL MATCH
    # ==================================================

    def family_key(row):

        brand = normalize_sku_text(row.get("brand", ""))
        name = normalize_sku_text(row.get("product_name_clean", ""))

        tokens = name.split()

        important_tokens = [
            t for t in tokens
            if len(t) >= 4
        ][:3]

        return brand + "_" + "_".join(important_tokens)

    regional_df["family_key"] = regional_df.apply(
        family_key,
        axis=1
    )

    regional_df["commercial_overlap"] = (
        regional_df.groupby("family_key")["country"]
        .transform("nunique")
    )

    # ==================================================
    # SAME SKU PRICE GAP
    # ==================================================

    regional_price_gap = (
        regional_df[
            regional_df["commercial_overlap"] > 1
        ]
        .groupby("family_key")
        .agg(
            countries=("country", "nunique"),
            retailers=("retailer", "nunique"),
            min_price_usd=("price_usd", "min"),
            max_price_usd=("price_usd", "max"),
            avg_price_usd=("price_usd", "mean"),
            product_name=("product_name", "first"),
            brand=("brand", "first"),
        )
        .reset_index()
    )

    regional_price_gap["price_gap_usd"] = (
        regional_price_gap["max_price_usd"]
        - regional_price_gap["min_price_usd"]
    )

    regional_price_gap["price_gap_pct"] = np.where(
        regional_price_gap["min_price_usd"] > 0,
        (
            regional_price_gap["price_gap_usd"]
            / regional_price_gap["min_price_usd"]
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
                    "min_price_usd",
                    "max_price_usd",
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

    regional_csv = (
        REGIONAL_OUTPUT
        / f"caribbean_master_{TIMESTAMP}.csv"
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
        regional_excel,
        engine="openpyxl"
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

    print("\n===================================")
    print(" REGIONAL FILES CREATED")
    print("===================================\n")

    print(f"Excel: {regional_excel}")
    print(f"CSV: {regional_csv}")
    print(f"TXT: {regional_txt}")
    print(f"JSONL: {regional_jsonl}")


# ======================================================
# MAIN
# ======================================================

def main():

    print("\n===================================")
    print(" CARIBBEAN RETAIL INTELLIGENCE AI")
    print("===================================\n")

    run_script(
        BASE_DIR / "scrapers/rd_retail_intelligence.py",
        "RD SCRAPER"
    )

    run_script(
        BASE_DIR / "scrapers/guyana_retail_intelligence.py",
        "GUYANA SCRAPER"
    )

    run_script(
        BASE_DIR / "scrapers/superfood_aruba_intelligence.py",
        "ARUBA SCRAPER"
    )

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