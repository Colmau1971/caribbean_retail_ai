
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np

# ==============================
# CONFIG
# ==============================

st.set_page_config(
    page_title="Caribbean Retail Intelligence",
    page_icon="🌎",
    layout="wide"
)

st.title("🌎 Caribbean Retail Intelligence Dashboard")
st.caption("Pricing, assortment and opportunity intelligence for Caribbean markets")

# ==============================
# LOAD DATA
# ==============================

@st.cache_data
def load_data():

    from glob import glob

    possible_files = sorted(
        glob("outputs/regional/caribbean_master_*.xlsx"),
        reverse=True
    )

    if not possible_files:

        st.error(
            "No encontré el archivo master "
            "en outputs/regional/"
        )

        st.stop()

    file_path = possible_files[0]

    st.success(f"Archivo cargado: {file_path}")

    df = pd.read_excel(file_path)

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    return df

df = load_data()
# ==============================
# COLUMN NORMALIZATION
# ==============================

if "standard_category" not in df.columns and "category" in df.columns:
    df["standard_category"] = df["category"]

if "price_per_kg_usd" not in df.columns:
    if "price_usd" in df.columns and "weight_kg" in df.columns:
        df["price_per_kg_usd"] = df["price_usd"] / df["weight_kg"]

for col in ["country", "standard_category", "retailer", "brand"]:
    if col not in df.columns:
        df[col] = "N/A"

# ==============================
# SIDEBAR FILTERS
# ==============================

st.sidebar.header("Filtros")

countries = st.sidebar.multiselect(
    "País",
    sorted(df["country"].dropna().unique()),
    default=sorted(df["country"].dropna().unique())
)

categories = st.sidebar.multiselect(
    "Categoría",
    sorted(df["standard_category"].dropna().unique()),
    default=sorted(df["standard_category"].dropna().unique())
)

retailers = st.sidebar.multiselect(
    "Retailer",
    sorted(df["retailer"].dropna().astype(str).unique())
)

brands = st.sidebar.multiselect(
    "Marca",
    sorted(df["brand"].dropna().astype(str).unique())
)

filtered = df[
    df["country"].isin(countries)
    & df["standard_category"].isin(categories)
].copy()

if retailers:
    filtered = filtered[filtered["retailer"].astype(str).isin(retailers)]

if brands:
    filtered = filtered[filtered["brand"].astype(str).isin(brands)]

# ==============================
# KPIs
# ==============================

total_skus = len(filtered)
total_countries = filtered["country"].nunique()
total_categories = filtered["standard_category"].nunique()
avg_price_kg = filtered["price_per_kg_usd"].mean() if "price_per_kg_usd" in filtered.columns else None

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Total SKUs", f"{total_skus:,.0f}")
kpi2.metric("Países", f"{total_countries}")
kpi3.metric("Categorías", f"{total_categories}")
kpi4.metric("Precio prom. USD/kg", f"${avg_price_kg:,.2f}" if pd.notna(avg_price_kg) else "N/A")

st.divider()

# ==============================
# PRICE INTELLIGENCE
# ==============================

st.subheader("💵 Pricing Intelligence")

col1, col2 = st.columns(2)

with col1:
    price_country = (
        filtered.dropna(subset=["price_per_kg_usd"])
        .groupby(["country", "standard_category"], as_index=False)
        .agg(avg_price_kg=("price_per_kg_usd", "mean"))
    )

    if not price_country.empty:
        fig = px.bar(
            price_country,
            x="standard_category",
            y="avg_price_kg",
            color="country",
            barmode="group",
            title="Precio promedio USD/kg por país y categoría"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes de USD/kg para esta vista.")

with col2:
    top_brands = (
        filtered.groupby("brand", as_index=False)
        .agg(skus=("brand", "count"))
        .sort_values("skus", ascending=False)
        .head(15)
    )

    fig = px.bar(
        top_brands,
        x="skus",
        y="brand",
        orientation="h",
        title="Top marcas por número de SKUs"
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

# ==============================
# OPPORTUNITY ENGINE
# ==============================

st.subheader("🚀 Opportunity Engine")

opportunity = (
    filtered.dropna(subset=["price_per_kg_usd"])
    .groupby(["country", "standard_category"], as_index=False)
    .agg(
        avg_price_kg=("price_per_kg_usd", "mean"),
        sku_count=("brand", "count"),
        brand_count=("brand", "nunique")
    )
)

if not opportunity.empty:
    opportunity["opportunity_score"] = (
        opportunity["avg_price_kg"].rank(pct=True) * 0.50
        + (1 / (opportunity["sku_count"] + 1)).rank(pct=True) * 0.30
        + (1 / (opportunity["brand_count"] + 1)).rank(pct=True) * 0.20
    ) * 100

    opportunity["opportunity_score"] = opportunity["opportunity_score"].round(1)

    def recommendation(score):
        if score >= 70:
            return "GO"
        if score >= 45:
            return "WATCH"
        return "NO GO"

    opportunity["recommendation"] = opportunity["opportunity_score"].apply(recommendation)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.scatter(
            opportunity,
            x="sku_count",
            y="avg_price_kg",
            size="opportunity_score",
            color="recommendation",
            hover_data=["country", "standard_category", "brand_count"],
            title="Opportunity Matrix: surtido vs precio/kg"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        top_opp = opportunity.sort_values("opportunity_score", ascending=False).head(10)

        fig = px.bar(
            top_opp,
            x="opportunity_score",
            y="standard_category",
            color="country",
            orientation="h",
            title="Top oportunidades regionales"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        opportunity.sort_values("opportunity_score", ascending=False),
        use_container_width=True
    )
else:
    st.info("No hay datos suficientes para calcular Opportunity Score.")
# ==============================
# SAME SKU CROSS COUNTRY
# ==============================

st.subheader("🌎 Same SKU Cross Country")

match_col = None

if "family_key" in filtered.columns:
    match_col = "family_key"

elif "match_key" in filtered.columns:
    match_col = "match_key"

elif "barcode_harmonized" in filtered.columns:
    match_col = "barcode_harmonized"

elif "barcode" in filtered.columns:
    match_col = "barcode"

if match_col:

    sku_cross = (
        filtered[
            filtered[match_col].notna()
        ]
        .groupby(match_col, as_index=False)
        .agg(
            countries=("country", "nunique"),
            retailers=("retailer", "nunique"),
            brand=("brand", "first"),
            product_name=("product_name", "first"),
            min_price=("price_usd", "min"),
            max_price=("price_usd", "max"),
            avg_price=("price_usd", "mean")
        )
    )

    sku_cross = sku_cross[
        sku_cross["countries"] > 1
    ]

    if not sku_cross.empty:

        sku_cross["price_gap_pct"] = np.where(
            sku_cross["min_price"] > 0,
            (
                sku_cross["max_price"]
                - sku_cross["min_price"]
            )
            / sku_cross["min_price"] * 100,
            np.nan
        )

        sku_cross = sku_cross.sort_values(
            "price_gap_pct",
            ascending=False
        )

        col5, col6 = st.columns(2)

        with col5:

            fig = px.scatter(
                sku_cross.head(100),
                x="min_price",
                y="max_price",
                size="price_gap_pct",
                color="countries",
                hover_data=[
                    "brand",
                    "product_name"
                ],
                title="Regional SKU Arbitrage"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col6:

            st.dataframe(
                sku_cross.head(50),
                use_container_width=True
            )

    else:

        st.info(
            "No se encontraron SKUs "
            "compartidos entre países."
        )

else:

    st.info(
        "No existe columna "
        "family_key/match_key."
    )
    
# ==============================
# PRICE ALERTS
# ==============================

st.subheader("🚨 Price Alerts")

alerts_path = Path(
    "outputs/regional/alerts/price_alerts.xlsx"
)

if alerts_path.exists():

    try:

        price_changes = pd.read_excel(
            alerts_path,
            sheet_name="Price Changes"
        )

        new_skus = pd.read_excel(
            alerts_path,
            sheet_name="New SKUs"
        )

        delisted_skus = pd.read_excel(
            alerts_path,
            sheet_name="Delisted SKUs"
        )

        a1, a2, a3 = st.columns(3)

        a1.metric(
            "Cambios precio",
            len(price_changes)
        )

        a2.metric(
            "Nuevos SKUs",
            len(new_skus)
        )

        a3.metric(
            "Delisted SKUs",
            len(delisted_skus)
        )

        if not price_changes.empty:

            price_changes["movement"] = np.where(
                price_changes["price_change_pct"] > 0,
                "Increase",
                "Decrease"
            )

            fig = px.histogram(
                price_changes,
                x="price_change_pct",
                color="movement",
                nbins=40,
                title="Distribución cambios de precio (%)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.dataframe(
                price_changes.sort_values(
                    "price_change_pct",
                    ascending=False
                ),
                use_container_width=True
            )

        with st.expander("🆕 Nuevos SKUs"):
            st.dataframe(
                new_skus,
                use_container_width=True
            )

        with st.expander("❌ Delisted SKUs"):
            st.dataframe(
                delisted_skus,
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"Error cargando alerts: {e}"
        )

else:

    st.info(
        "No existe price_alerts.xlsx"
    )    
# ==============================
# RETAILER BENCHMARK
# ==============================

st.subheader("🏪 Retailer Benchmark")

retailer_view = (
    filtered.groupby(["country", "retailer"], as_index=False)
    .agg(
        sku_count=("brand", "count"),
        brands=("brand", "nunique"),
        avg_price_usd=("price_usd", "mean") if "price_usd" in filtered.columns else ("brand", "count"),
        avg_price_kg=("price_per_kg_usd", "mean")
    )
    .sort_values("sku_count", ascending=False)
)

st.dataframe(retailer_view, use_container_width=True)

# ==============================
# RAW DATA
# ==============================

with st.expander("Ver data filtrada"):
    st.dataframe(filtered, use_container_width=True)
