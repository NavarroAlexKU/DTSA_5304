import streamlit as st
import pandas as pd
import os
import altair as alt
import kagglehub

st.set_page_config(layout="wide")
st.title("Vehicle Price Dashboard")

@st.cache_data
def load_df():
    path = kagglehub.dataset_download("ayeshasiddiqa123/cars-pre")
    csv_path = os.path.join(path, "car_price_prediction_.csv")
    return pd.read_csv(csv_path)

df = load_df()

# ===============================
# MULTI-SELECT SLICERS (SYNCED)
# - Empty selection = "All"
# ===============================
with st.sidebar:
    st.header("Filters")

    brand_all = sorted(df["Brand"].dropna().unique().tolist())
    brands = st.multiselect("Brand(s)", brand_all, key="brands")

    # Models depend on selected brands
    if brands:
        model_all = sorted(
            df.loc[df["Brand"].isin(brands), "Model"].dropna().unique().tolist()
        )
    else:
        model_all = sorted(df["Model"].dropna().unique().tolist())

    # Reset models if they contain values not valid under current brand selection
    if "models" not in st.session_state:
        st.session_state.models = []
    st.session_state.models = [m for m in st.session_state.models if m in model_all]

    models = st.multiselect("Model(s)", model_all, key="models")

    # Years depend on selected brands + models
    tmp = df
    if brands:
        tmp = tmp[tmp["Brand"].isin(brands)]
    if models:
        tmp = tmp[tmp["Model"].isin(models)]

    year_all = sorted(tmp["Year"].dropna().unique().tolist())

    # Reset years if they contain values not valid under current selections
    if "years" not in st.session_state:
        st.session_state.years = []
    st.session_state.years = [y for y in st.session_state.years if y in year_all]

    years = st.multiselect("Year(s)", year_all, key="years")

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
