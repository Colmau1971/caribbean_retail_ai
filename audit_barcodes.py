import pandas as pd

df = pd.read_csv(
    "outputs/regional/caribbean_master_latest.csv",
    low_memory=False
)

df["barcode"] = df["barcode"].astype(str).str.strip()

df = df[
    (df["barcode"] != "") &
    (df["barcode"] != "<NA>") &
    (df["barcode"] != "nan")
].copy()

audit = (
    df.groupby("barcode")
      .agg(
          products=("product_name", "nunique"),
          rows=("product_name", "count"),
          countries=("country", "nunique"),
          retailers=("retailer", "nunique"),
          sample_product=("product_name", "first")
      )
      .reset_index()
      .sort_values(
          ["countries", "retailers", "products"],
          ascending=False
      )
)

audit.to_excel("barcode_audit.xlsx", index=False)

print(audit.head(30).to_string(index=False))
print()
print("Barcodes únicos:", len(audit))
print("Archivo creado: barcode_audit.xlsx")
