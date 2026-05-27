from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")

REGIONAL_DIR = BASE_DIR / "outputs/regional"

ALERT_DIR = REGIONAL_DIR / "alerts"
ALERT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(
    REGIONAL_DIR.glob("*.csv"),
    key=lambda x: x.stat().st_mtime
)

if len(files) < 2:
    print("Se necesitan al menos 2 snapshots regionales.")
    exit()

previous_file = files[-2]
latest_file = files[-1]

print("Anterior:", previous_file)
print("Actual:", latest_file)

prev = pd.read_csv(previous_file)
curr = pd.read_csv(latest_file)

prev.columns = [str(c).strip().lower() for c in prev.columns]
curr.columns = [str(c).strip().lower() for c in curr.columns]

match_col = None

for c in ["match_key", "family_key", "barcode_harmonized", "barcode"]:
    if c in curr.columns and c in prev.columns:
        match_col = c
        break

if not match_col:
    print("No encontré llave de comparación.")
    exit()

key_cols = ["country", "retailer", match_col]

prev_price = prev[
    key_cols + ["brand", "product_name", "price_usd"]
].dropna(subset=["price_usd"])

curr_price = curr[
    key_cols + ["brand", "product_name", "price_usd"]
].dropna(subset=["price_usd"])

merged = curr_price.merge(
    prev_price,
    on=key_cols,
    how="outer",
    suffixes=("_current", "_previous"),
    indicator=True
)

merged["price_change_pct"] = np.where(
    merged["price_usd_previous"] > 0,
    (
        merged["price_usd_current"]
        - merged["price_usd_previous"]
    )
    / merged["price_usd_previous"] * 100,
    np.nan
)

price_changes = merged[
    (merged["_merge"] == "both")
    & (merged["price_change_pct"].abs() >= 5)
].copy()

new_skus = merged[
    merged["_merge"] == "left_only"
].copy()

delisted_skus = merged[
    merged["_merge"] == "right_only"
].copy()

output_excel = ALERT_DIR / "price_alerts.xlsx"
output_csv = ALERT_DIR / "price_changes.csv"

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    price_changes.to_excel(writer, sheet_name="Price Changes", index=False)
    new_skus.to_excel(writer, sheet_name="New SKUs", index=False)
    delisted_skus.to_excel(writer, sheet_name="Delisted SKUs", index=False)

price_changes.to_csv(output_csv, index=False, encoding="utf-8-sig")

print("\n===================================")
print(" PRICE ALERTS CREATED")
print("===================================")
print("Cambios precio:", len(price_changes))
print("Nuevos SKUs:", len(new_skus))
print("Delisted SKUs:", len(delisted_skus))
print("Excel:", output_excel)
print("CSV:", output_csv)