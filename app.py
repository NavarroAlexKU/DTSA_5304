import streamlit as st
import pandas as pd
import os
import altair as alt

st.set_page_config(layout="wide")
st.title("Vehicle Price Dashboard")

@st.cache_data
def load_df():
    return pd.read_csv("data/car_price_prediction_.csv")

df = load_df()

# ===============================
# MULTI-SELECT SLICERS (SYNCED)
# - Empty selection = "All"
# ===============================
with st.sidebar:
    st.header("Filters")

    # --- Brand ---
    brand_all = sorted(df["Brand"].dropna().unique().tolist())
    brands = st.multiselect("Brand(s)", brand_all, key="brands")

    # --- Model (depends on Brand) ---
    if brands:
        model_all = sorted(df.loc[df["Brand"].isin(brands), "Model"].dropna().unique().tolist())
    else:
        model_all = sorted(df["Model"].dropna().unique().tolist())

    if "models" not in st.session_state:
        st.session_state.models = []
    st.session_state.models = [m for m in st.session_state.models if m in model_all]

    models = st.multiselect("Model(s)", model_all, key="models")

    # Build tmp for downstream dependent slicers
    tmp = df
    if brands:
        tmp = tmp[tmp["Brand"].isin(brands)]
    if models:
        tmp = tmp[tmp["Model"].isin(models)]

    # --- Year (depends on Brand + Model) ---
    year_all = sorted(tmp["Year"].dropna().unique().tolist())

    if "years" not in st.session_state:
        st.session_state.years = []
    st.session_state.years = [y for y in st.session_state.years if y in year_all]

    years = st.multiselect("Year(s)", year_all, key="years")

    # Apply Year to tmp for the remaining slicers
    if years:
        tmp = tmp[tmp["Year"].isin(years)]

    # --- Transmission (depends on Brand + Model + Year) ---
    transmission_all = sorted(tmp["Transmission"].dropna().unique().tolist())
    if "transmissions" not in st.session_state:
        st.session_state.transmissions = []
    st.session_state.transmissions = [t for t in st.session_state.transmissions if t in transmission_all]
    transmissions = st.multiselect("Transmission(s)", transmission_all, key="transmissions")

    if transmissions:
        tmp = tmp[tmp["Transmission"].isin(transmissions)]

    # --- Condition (depends on previous filters) ---
    condition_all = sorted(tmp["Condition"].dropna().unique().tolist())
    if "conditions" not in st.session_state:
        st.session_state.conditions = []
    st.session_state.conditions = [c for c in st.session_state.conditions if c in condition_all]
    conditions = st.multiselect("Condition(s)", condition_all, key="conditions")

    if conditions:
        tmp = tmp[tmp["Condition"].isin(conditions)]

    # --- Engine Size (depends on previous filters) ---
    engine_all = sorted(tmp["Engine Size"].dropna().unique().tolist())
    if "engine_sizes" not in st.session_state:
        st.session_state.engine_sizes = []
    st.session_state.engine_sizes = [e for e in st.session_state.engine_sizes if e in engine_all]
    engine_sizes = st.multiselect("Engine Size(s)", engine_all, key="engine_sizes")

    if engine_sizes:
        tmp = tmp[tmp["Engine Size"].isin(engine_sizes)]

    # --- Fuel Type (depends on previous filters) ---
    fuel_all = sorted(tmp["Fuel Type"].dropna().unique().tolist())
    if "fuel_types" not in st.session_state:
        st.session_state.fuel_types = []
    st.session_state.fuel_types = [f for f in st.session_state.fuel_types if f in fuel_all]
    fuel_types = st.multiselect("Fuel Type(s)", fuel_all, key="fuel_types")


# ===============================
# APPLY FILTERS
# ===============================
filtered = df
if brands:
    filtered = filtered[filtered["Brand"].isin(brands)]
if models:
    filtered = filtered[filtered["Model"].isin(models)]
if years:
    filtered = filtered[filtered["Year"].isin(years)]
if transmissions:
    filtered = filtered[filtered["Transmission"].isin(transmissions)]
if conditions:
    filtered = filtered[filtered["Condition"].isin(conditions)]
if engine_sizes:
    filtered = filtered[filtered["Engine Size"].isin(engine_sizes)]
if fuel_types:
    filtered = filtered[filtered["Fuel Type"].isin(fuel_types)]


# ===============================
# FILTERED SUMMARY (KPIs)
# ===============================
st.markdown("### Vehicle Pricing Summary")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Vehicles", f"{len(filtered):,}")

c2.metric(
    "Minimum Price",
    f"${filtered['Price'].min():,.0f}" if len(filtered) else "—"
)

c3.metric(
    "Median Price",
    f"${filtered['Price'].median():,.0f}" if len(filtered) else "—"
)

c4.metric(
    "Max Price",
    f"${filtered['Price'].max():,.0f}" if len(filtered) else "—"
)

if filtered.empty:
    st.warning("No rows match the current filters. Try removing one filter.")
    st.stop()

# ===============================
# CHARTS
# ===============================
brand_count_plot = (
    alt.Chart(filtered)
    .mark_bar()
    .encode(
        x=alt.X("Year:O", title="Model Year", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("count():Q", title="Number of Vehicles"),
        color=alt.Color("Brand:N", title="Brand"),
        tooltip=["Year:O", "Brand:N", "count():Q"],
    )
    .properties(height=300, title="Vehicle Count by Model Year (Colored by Brand)")
)

detailed_dist = (
    alt.Chart(filtered)
    .mark_boxplot()
    .encode(
        x=alt.X("Model:N", title="Vehicle Model", axis=alt.Axis(labelAngle=-45, labelLimit=120)),
        y=alt.Y("Price:Q", title="Price ($)"),
        color=alt.Color("Model:N", legend=None),
        tooltip=["Brand:N", "Year:O", "Model:N", alt.Tooltip("Price:Q", format=",.0f")],
    )
    .properties(height=300, title="Price Distribution by Model (Boxplot)")
)

yearly_uplift = (
    alt.Chart(filtered)
    .transform_aggregate(median_price="median(Price)", groupby=["Year"])
    .transform_window(
        baseline_price="first_value(median_price)",
        sort=[alt.SortField("Year", order="ascending")],
    )
    .transform_calculate(
        pct_diff_vs_baseline="""
        datum.baseline_price == 0 ? 0 :
        (datum.median_price - datum.baseline_price) / datum.baseline_price * 100
        """
    )
)

uplift_chart = (
    yearly_uplift
    .mark_bar()
    .encode(
        x=alt.X("Year:O", title="Model Year", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y(
            "pct_diff_vs_baseline:Q",
            title="% Difference vs Oldest Model Year",
            axis=alt.Axis(format=".1f"),
        ),
        color=alt.Color(
            "pct_diff_vs_baseline:Q",
            scale=alt.Scale(domain=[-100, 0, 100], range=["#d73027", "#f0f0f0", "#1a9850"]),
            legend=alt.Legend(title="% Difference"),
        ),
        tooltip=[
            "Year:O",
            alt.Tooltip("median_price:Q", title="Median Price", format=",.0f"),
            alt.Tooltip("pct_diff_vs_baseline:Q", title="% vs Baseline", format=".2f"),
        ],
    )
    .properties(
        height=300,
        title={
            "text": "Median Price Difference by Model Year",
            "subtitle": "Baseline = median price of the oldest model year after filters",
        },
    )
)

dashboard = alt.vconcat(
    brand_count_plot,
    detailed_dist,
    uplift_chart
).resolve_scale(color="independent")

st.altair_chart(dashboard, width="stretch")

# ===============================
# MILEAGE IMPACT ON PRICE
# ===============================

st.markdown("### Mileage vs Price")

# Clean numeric fields
mileage_df = filtered.copy()
mileage_df["Mileage"] = pd.to_numeric(mileage_df["Mileage"], errors="coerce")
mileage_df["Price"] = pd.to_numeric(mileage_df["Price"], errors="coerce")
mileage_df = mileage_df.dropna(subset=["Mileage", "Price"])

if mileage_df.empty:
    st.info("Mileage/Price chart unavailable: Mileage or Price is missing after filters.")
else:
    # Controls
    cA, cB, cC = st.columns([1.2, 1.2, 1.6])

    with cA:
        use_quantiles = st.checkbox("Use quantile mileage buckets", value=False)
    with cB:
        price_stat = st.selectbox("Price summary", ["Median", "Mean"], index=0)
    with cC:
        # Keep outlier mileage from dominating bucket ranges
        m_cap = st.slider(
            "Max mileage to include (cap)",
            min_value=0,
            max_value=int(mileage_df["Mileage"].quantile(0.999)),
            value=int(mileage_df["Mileage"].quantile(0.99)),
            step=1000,
        )

    mileage_df = mileage_df[mileage_df["Mileage"] <= m_cap]

    # Build buckets
    if use_quantiles:
        # 10 quantile buckets
        try:
            mileage_df["Mileage_Bucket"] = pd.qcut(
                mileage_df["Mileage"],
                q=10,
                duplicates="drop",
            ).astype(str)
        except ValueError:
            # Fallback if too few unique mileage values
            use_quantiles = False

    if not use_quantiles:
        # Fixed buckets (miles)
        bins = [0, 25_000, 50_000, 75_000, 100_000, 150_000, 200_000, 300_000, 1_000_000]
        labels = ["0–25k", "25–50k", "50–75k", "75–100k", "100–150k", "150–200k", "200–300k", "300k+"]
        mileage_df["Mileage_Bucket"] = pd.cut(
            mileage_df["Mileage"],
            bins=bins,
            labels=labels,
            include_lowest=True,
        ).astype(str)

    # Aggregate
    if price_stat == "Median":
        agg = (
            mileage_df.groupby("Mileage_Bucket", as_index=False)
            .agg(price_value=("Price", "median"), n=("Price", "size"))
        )
        y_title = "Median Price ($)"
    else:
        agg = (
            mileage_df.groupby("Mileage_Bucket", as_index=False)
            .agg(price_value=("Price", "mean"), n=("Price", "size"))
        )
        y_title = "Mean Price ($)"

    # Keep bucket order for fixed bins
    if not use_quantiles:
        bucket_order = labels
    else:
        bucket_order = agg["Mileage_Bucket"].tolist()

    mileage_price_chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("Mileage_Bucket:N", sort=bucket_order, title="Mileage Bucket (miles)", axis=alt.Axis(labelAngle=-30)),
            y=alt.Y("price_value:Q", title=y_title),
            tooltip=[
                alt.Tooltip("Mileage_Bucket:N", title="Mileage Bucket"),
                alt.Tooltip("price_value:Q", title=price_stat + " Price", format=",.0f"),
                alt.Tooltip("n:Q", title="Vehicles"),
            ],
        )
        .properties(height=320, title=f"{price_stat} Price by Mileage Bucket")
    )

    st.altair_chart(mileage_price_chart, width="stretch")

