from pathlib import Path
import pandas as pd
import numpy as np

INPUT_DIR = Path("outputs/regional")
OUTPUT_DIR = Path("outputs/regional/insights")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MASTER_FILE = sorted(INPUT_DIR.glob("caribbean_master_*.xlsx"))[-1]

print("Leyendo:", MASTER_FILE)

df = pd.read_excel(MASTER_FILE)

# =========================
# NORMALIZACIÓN
# =========================

df.columns = [str(c).strip().lower() for c in df.columns]

for col in ["country", "standard_category", "brand", "product_name", "retailer"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

# Posibles columnas de precio/peso
price_cols = ["price_usd", "price", "precio", "precio_usd", "price_local"]
weight_cols = ["weight_kg", "weight_g", "grams", "gramaje", "peso_g"]

price_col = next((c for c in price_cols if c in df.columns), None)
weight_col = next((c for c in weight_cols if c in df.columns), None)

# =========================
# PRICE PER KG
# =========================

if "price_per_kg_usd" in df.columns:

    df["price_per_kg"] = pd.to_numeric(
        df["price_per_kg_usd"],
        errors="coerce"
    )

elif weight_col is None:

    print("No encontré peso. Se calcularán insights sin precio/kg.")
    df["price_per_kg"] = np.nan

else:

    df[price_col] = pd.to_numeric(
        df[price_col],
        errors="coerce"
    )

    df[weight_col] = pd.to_numeric(
        df[weight_col],
        errors="coerce"
    )

    if weight_col == "weight_kg":
        df["price_per_kg"] = (
            df[price_col] / df[weight_col]
        )

    else:
        df["price_per_kg"] = (
            df[price_col] / (df[weight_col] / 1000)
        )
# =========================
# 1. TOP MARCAS REGIONALES
# =========================

top_brands = (
    df.groupby(["brand"], dropna=False)
    .agg(
        sku_count=("product_name", "count"),
        countries=("country", lambda x: x.nunique()),
        categories=("standard_category", lambda x: x.nunique()),
        avg_price_kg=("price_per_kg", "mean")
    )
    .reset_index()
    .sort_values("sku_count", ascending=False)
)

# =========================
# 2. PRECIO PROMEDIO POR CATEGORÍA Y PAÍS
# =========================

avg_price_category = (
    df.groupby(["country", "standard_category"], dropna=False)
    .agg(
        sku_count=("product_name", "count"),
        avg_price=("price_per_kg", "mean"),
        min_price=("price_per_kg", "min"),
        max_price=("price_per_kg", "max")
    )
    .reset_index()
    .sort_values(["standard_category", "country"])
)

# =========================
# 3. GAPS RD VS GUYANA
# =========================

pivot = avg_price_category.pivot_table(
    index="standard_category",
    columns="country",
    values="avg_price"
).reset_index()

if "Dominican Republic" in pivot.columns and "Guyana" in pivot.columns:
    pivot["gap_guyana_vs_rd_%"] = (
        (pivot["Guyana"] / pivot["Dominican Republic"]) - 1
    ) * 100
else:
    pivot["gap_guyana_vs_rd_%"] = np.nan

gaps_rd_guyana = pivot.sort_values("gap_guyana_vs_rd_%", ascending=False)
# =========================
# 3B. SAME SKU CROSS COUNTRY
# =========================

match_col = None

if "family_key" in df.columns:
    match_col = "family_key"

elif "match_key" in df.columns:
    match_col = "match_key"

elif "barcode_harmonized" in df.columns:
    match_col = "barcode_harmonized"

elif "barcode" in df.columns:
    match_col = "barcode"

if match_col:

    same_sku_cross_country = (
        df[
            df[match_col].notna()
        ]
        .groupby(match_col)
        .agg(
            countries=("country", "nunique"),
            retailers=("retailer", "nunique"),
            sku_records=("product_name", "count"),
            brand=("brand", "first"),
            product_name=("product_name", "first"),
            min_price_usd=("price_usd", "min"),
            max_price_usd=("price_usd", "max"),
            avg_price_usd=("price_usd", "mean"),
            min_price_kg=("price_per_kg", "min"),
            max_price_kg=("price_per_kg", "max"),
            avg_price_kg=("price_per_kg", "mean"),
        )
        .reset_index()
    )

    same_sku_cross_country = (
        same_sku_cross_country[
            same_sku_cross_country["countries"] > 1
        ]
        .copy()
    )

    same_sku_cross_country["price_gap_usd"] = (
        same_sku_cross_country["max_price_usd"]
        - same_sku_cross_country["min_price_usd"]
    )

    same_sku_cross_country["price_gap_pct"] = np.where(
        same_sku_cross_country["min_price_usd"] > 0,
        (
            same_sku_cross_country["price_gap_usd"]
            / same_sku_cross_country["min_price_usd"]
        ) * 100,
        np.nan
    )

    same_sku_cross_country = (
        same_sku_cross_country.sort_values(
            "price_gap_pct",
            ascending=False
        )
    )

else:

    same_sku_cross_country = pd.DataFrame()
# =========================
# 4. OPORTUNIDADES PREMIUM
# =========================

premium_threshold = (
    df.groupby(["country", "standard_category"])["price_per_kg"]
    .quantile(0.75)
    .reset_index()
    .rename(columns={"price_per_kg": "premium_threshold"})
)

df_premium = df.merge(
    premium_threshold,
    on=["country", "standard_category"],
    how="left"
)

premium_opportunities = df_premium[
    df_premium["price_per_kg"] >= df_premium["premium_threshold"]
].copy()

premium_opportunities = premium_opportunities.sort_values(
    "price_per_kg", ascending=False
)

# =========================
# 5. BENCHMARK BIMBO
# =========================

bimbo_keywords = ["bimbo", "marinela", "tía rosa", "tia rosa", "barcel", "takis", "wonder"]

df["is_bimbo"] = df["brand"].str.lower().apply(
    lambda x: any(k in x for k in bimbo_keywords)
)

benchmark_bimbo = (
    df.groupby(["country", "standard_category", "is_bimbo"])
    .agg(
        sku_count=("product_name", "count"),
        avg_price_kg=("price_per_kg", "mean")
    )
    .reset_index()
)

# =========================
# 6. ALERTAS DE MERCADO
# =========================

alerts = []

for _, row in gaps_rd_guyana.iterrows():
    cat = row["standard_category"]
    gap = row.get("gap_guyana_vs_rd_%", np.nan)

    if pd.notna(gap):
        if gap > 25:
            alerts.append({
                "type": "Premium Gap",
                "category": cat,
                "message": f"Guyana presenta precio/kg {gap:.1f}% superior a RD. Posible oportunidad premium o mercado importado.",
                "priority": "Alta"
            })
        elif gap < -20:
            alerts.append({
                "type": "Price Pressure",
                "category": cat,
                "message": f"Guyana presenta precio/kg {abs(gap):.1f}% inferior a RD. Revisar competitividad de entrada.",
                "priority": "Media"
            })

for _, row in avg_price_category.iterrows():
    if row["sku_count"] < 10:
        alerts.append({
            "type": "Low Assortment",
            "category": row["standard_category"],
            "message": f"{row['country']} tiene baja profundidad de surtido en {row['standard_category']} ({row['sku_count']} SKUs).",
            "priority": "Media"
        })

alerts_df = pd.DataFrame(alerts)

# =========================
# 7. RESUMEN EJECUTIVO TXT
# =========================

summary_path = OUTPUT_DIR / "regional_executive_summary.txt"

with open(summary_path, "w", encoding="utf-8") as f:
    f.write("CARIBBEAN RETAIL INTELLIGENCE ENGINE\n")
    f.write("====================================\n\n")

    f.write("1. Top marcas regionales\n")
    f.write(top_brands.head(10).to_string(index=False))
    f.write("\n\n")

    f.write("2. Gaps RD vs Guyana\n")
    f.write(gaps_rd_guyana.to_string(index=False))
    f.write("\n\n")

    f.write("3. Alertas de entrada mercado\n")
    if not alerts_df.empty:
        f.write(alerts_df.to_string(index=False))
    else:
        f.write("Sin alertas críticas detectadas.")
    f.write("\n")
    f.write("3B. Same SKU Cross Country\n")
    if not same_sku_cross_country.empty:
        f.write(same_sku_cross_country.head(20).to_string(index=False))
    else:
        f.write("No se encontraron SKUs con barcode compartido entre países.")
    f.write("\n\n")
# =========================
# 8. EXPORT EXCEL
# =========================

output_excel = OUTPUT_DIR / "regional_insights.xlsx"

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    top_brands.to_excel(writer, sheet_name="Top Brands", index=False)
    avg_price_category.to_excel(writer, sheet_name="Avg Price Category", index=False)
    gaps_rd_guyana.to_excel(writer, sheet_name="RD vs Guyana Gaps", index=False)
    premium_opportunities.to_excel(writer, sheet_name="Premium Opportunities", index=False)
    benchmark_bimbo.to_excel(writer, sheet_name="Benchmark Bimbo", index=False)
    alerts_df.to_excel(writer, sheet_name="Market Alerts", index=False)
    same_sku_cross_country.to_excel(writer, sheet_name="Same SKU Cross Country", index=False)
    
print("\n===================================")
print(" REGIONAL INSIGHTS FINISHED")
print("===================================")
print("Excel:", output_excel)
print("Summary:", summary_path)