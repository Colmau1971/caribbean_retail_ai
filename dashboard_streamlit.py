import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np
from glob import glob

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

    preferred_files = [
        "outputs/regional/caribbean_master_latest.xlsx",
        "outputs/regional/caribbean_master_latest.csv",
    ]

    file_path = None

    for candidate in preferred_files:
        if Path(candidate).exists():
            file_path = candidate
            break

    if file_path is None:
        possible_files = sorted(
            glob("outputs/regional/caribbean_master_*.xlsx"),
            reverse=True
        )

        if not possible_files:
            st.error(
                "No encontré el archivo master en outputs/regional/."
            )
            st.stop()

        file_path = possible_files[0]

    st.success(f"Archivo cargado: {file_path}")

    if str(file_path).endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
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

if "brand_group" not in df.columns:
    df["brand_group"] = df["brand"]

if "product_name" not in df.columns:
    df["product_name"] = "N/A"

if "price_usd" not in df.columns:
    df["price_usd"] = np.nan

if "price_per_kg_usd" not in df.columns:
    df["price_per_kg_usd"] = np.nan

for col in ["price_usd", "price_per_kg_usd"]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

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

brand_groups = st.sidebar.multiselect(
    "Marca homologada / Grupo",
    sorted(df["brand_group"].dropna().astype(str).unique())
)

filtered = df[
    df["country"].isin(countries)
    & df["standard_category"].isin(categories)
].copy()

if retailers:
    filtered = filtered[
        filtered["retailer"].astype(str).isin(retailers)
    ]

if brands:
    filtered = filtered[
        filtered["brand"].astype(str).isin(brands)
    ]

if brand_groups:
    filtered = filtered[
        filtered["brand_group"].astype(str).isin(brand_groups)
    ]

# ==============================
# KPIs
# ==============================

total_records = len(filtered)

if "family_key" in filtered.columns:
    unique_skus = filtered["family_key"].nunique()
elif "match_key" in filtered.columns:
    unique_skus = filtered["match_key"].nunique()
elif "barcode_harmonized" in filtered.columns:
    unique_skus = filtered["barcode_harmonized"].nunique()
elif "barcode" in filtered.columns:
    unique_skus = filtered["barcode"].nunique()
else:
    unique_skus = filtered["product_name"].nunique()

total_countries = filtered["country"].nunique()
total_categories = filtered["standard_category"].nunique()

avg_price_kg = filtered["price_per_kg_usd"].median()

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric("Total Records", f"{total_records:,.0f}")
kpi2.metric("Unique SKUs", f"{unique_skus:,.0f}")
kpi3.metric("Países", f"{total_countries}")
kpi4.metric("Categorías", f"{total_categories}")
kpi5.metric(
    "Precio prom. USD/kg",
    f"${avg_price_kg:,.2f}" if pd.notna(avg_price_kg) else "N/A"
)

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
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay datos suficientes de USD/kg para esta vista.")

with col2:
    top_brands = (
        filtered.groupby("brand", as_index=False)
        .agg(skus=("brand", "count"))
        .sort_values("skus", ascending=False)
        .head(15)
    )

    if not top_brands.empty:
        fig = px.bar(
            top_brands,
            x="skus",
            y="brand",
            orientation="h",
            title="Top marcas por número de SKUs"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay datos suficientes de marcas.")

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
        st.plotly_chart(fig, width="stretch")

    with col4:
        top_opp = opportunity.sort_values(
            "opportunity_score",
            ascending=False
        ).head(10)

        fig = px.bar(
            top_opp,
            x="opportunity_score",
            y="standard_category",
            color="country",
            orientation="h",
            title="Top oportunidades regionales"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

    st.dataframe(
        opportunity.sort_values("opportunity_score", ascending=False),
        width="stretch"
    )
else:
    st.info("No hay datos suficientes para calcular Opportunity Score.")

# ==============================
# BRAND INTELLIGENCE
# ==============================

st.subheader("🏷️ Brand Intelligence")

view_type = st.radio(
    "Brand Analysis",
    ["Brand", "Brand Group"],
    horizontal=True
)

if view_type == "Brand":
    brand_col = "brand"
else:
    brand_col = "brand_group"

brand_view = (
    filtered.dropna(
        subset=[
            "country",
            brand_col,
            "price_per_kg_usd"
        ]
    )
    .groupby(
        ["country", brand_col],
        as_index=False
    )
    .agg(
        skus=("product_name", "count"),
        avg_price_kg_usd=("price_per_kg_usd", "mean"),
        min_price_kg_usd=("price_per_kg_usd", "min"),
        max_price_kg_usd=("price_per_kg_usd", "max")
    )
    .rename(columns={brand_col: "brand"})
)

if not brand_view.empty:
    top_brand_price = (
        brand_view
        .sort_values(
            "avg_price_kg_usd",
            ascending=False
        )
        .head(25)
    )

    fig = px.bar(
        top_brand_price,
        x="brand",
        y="avg_price_kg_usd",
        color="country",
        title="Top Brand Pricing (USD/kg)"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    st.dataframe(
        brand_view.sort_values(
            "avg_price_kg_usd",
            ascending=False
        ),
        width="stretch"
    )

    st.subheader("🌎 Brand Regional Presence")

    brand_presence = (
        brand_view
        .groupby("brand", as_index=False)
        .agg(
            countries=("country", "nunique"),
            total_skus=("skus", "sum"),
            avg_price_kg_usd=("avg_price_kg_usd", "mean")
        )
        .sort_values(
            ["countries", "total_skus"],
            ascending=False
        )
    )

    fig = px.scatter(
        brand_presence.head(40),
        x="total_skus",
        y="avg_price_kg_usd",
        size="countries",
        color="countries",
        hover_data=["brand"],
        title="Brand Presence vs Price Position"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    st.dataframe(
        brand_presence,
        width="stretch"
    )
else:
    st.info("No hay datos suficientes para Brand Intelligence.")

# ==============================
# COMPETITIVE LANDSCAPE
# ==============================

st.subheader("🏢 Competitive Landscape")

competitive = (
    filtered.dropna(
        subset=[
            "brand_group",
            "price_per_kg_usd"
        ]
    )
    .groupby("brand_group", as_index=False)
    .agg(
        countries=("country", "nunique"),
        skus=("product_name", "count"),
        avg_price_kg=("price_per_kg_usd", "mean"),
        min_price_kg=("price_per_kg_usd", "min"),
        max_price_kg=("price_per_kg_usd", "max")
    )
    .sort_values(
        ["countries", "skus"],
        ascending=False
    )
)

if not competitive.empty:
    fig = px.scatter(
        competitive.head(50),
        x="skus",
        y="avg_price_kg",
        size="countries",
        color="countries",
        hover_data=["brand_group", "min_price_kg", "max_price_kg"],
        title="Competitive Landscape: Presence vs Price Position"
    )

    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        competitive,
        width="stretch"
    )
else:
    st.info("No hay datos suficientes para Competitive Landscape.")

# ==============================
# CATEGORY INTELLIGENCE
# ==============================

st.subheader("📊 Category Intelligence")

category_intelligence_df = (
    filtered.dropna(
        subset=[
            "country",
            "standard_category",
            "price_per_kg_usd"
        ]
    )
    .groupby(
        ["country", "standard_category"],
        as_index=False
    )
    .agg(
        skus=("product_name", "count"),
        avg_price_kg_usd=("price_per_kg_usd", "mean"),
        median_price_kg_usd=("price_per_kg_usd", "median"),
        max_price_kg_usd=("price_per_kg_usd", "max")
    )
)

if not category_intelligence_df.empty:
    fig = px.bar(
        category_intelligence_df,
        x="standard_category",
        y="avg_price_kg_usd",
        color="country",
        barmode="group",
        title="Category Price Architecture"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    category_matrix = (
        category_intelligence_df
        .pivot_table(
            index="standard_category",
            columns="country",
            values="avg_price_kg_usd"
        )
        .round(2)
    )

    st.subheader("Regional Category Matrix USD/kg")

    st.dataframe(
        category_matrix,
        width="stretch"
    )

    st.subheader("📈 Category Index (RD = 100)")

    index_matrix = category_matrix.copy()

    if "Dominican Republic" in index_matrix.columns:
        rd_base = index_matrix["Dominican Republic"]

        index_matrix = (
            index_matrix
            .div(rd_base, axis=0)
            * 100
        ).round(0)

        st.dataframe(
            index_matrix,
            width="stretch"
        )

        index_long = (
            index_matrix
            .reset_index()
            .melt(
                id_vars="standard_category",
                var_name="country",
                value_name="index_vs_rd"
            )
        )

        fig = px.bar(
            index_long,
            x="standard_category",
            y="index_vs_rd",
            color="country",
            barmode="group",
            title="Category Price Index vs Dominican Republic"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )
    else:
        st.info("No se encontró Dominican Republic para calcular RD = 100.")
else:
    st.info("No hay datos suficientes para Category Intelligence.")

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
                width="stretch"
            )

        with col6:
            st.dataframe(
                sku_cross.head(50),
                width="stretch"
            )
    else:
        st.info(
            "No se encontraron SKUs compartidos entre países."
        )
else:
    st.info(
        "No existe columna family_key/match_key."
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

        a1.metric("Cambios precio", len(price_changes))
        a2.metric("Nuevos SKUs", len(new_skus))
        a3.metric("Delisted SKUs", len(delisted_skus))

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
                width="stretch"
            )

            st.dataframe(
                price_changes.sort_values(
                    "price_change_pct",
                    ascending=False
                ),
                width="stretch"
            )

        with st.expander("🆕 Nuevos SKUs"):
            st.dataframe(
                new_skus,
                width="stretch"
            )

        with st.expander("❌ Delisted SKUs"):
            st.dataframe(
                delisted_skus,
                width="stretch"
            )
    except Exception as e:
        st.error(f"Error cargando alerts: {e}")
else:
    st.info("No existe price_alerts.xlsx")

# ==============================
# RETAILER BENCHMARK
# ==============================

st.subheader("🏪 Retailer Benchmark")

retailer_view = (
    filtered.groupby(["country", "retailer"], as_index=False)
    .agg(
        sku_count=("brand", "count"),
        brands=("brand", "nunique"),
        avg_price_usd=("price_usd", "mean"),
        avg_price_kg=("price_per_kg_usd", "mean")
    )
    .sort_values("sku_count", ascending=False)
)

st.dataframe(retailer_view, width="stretch")

# ==============================
# RAW DATA
# ==============================

with st.expander("Ver data filtrada"):
    st.dataframe(filtered, width="stretch")
