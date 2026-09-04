# -*- coding: utf-8 -*-
"""Uganda Economic Pulse_Capstone Project

**Economic Monitoring, Risk Analysis & Growth Outlook**

Uganda Economic Pulse is a data-driven economic intelligence dashboard designed to monitor Uganda’s economic performance, identify emerging risks and assess the near-term growth outlook. Using automated public data ingestion, SQL analytics, interactive visualizations, risk scoring and GDP forecasting.

The dashboard transforms key economic indicators into actionable insights for understanding Uganda’s changing economic landscape.

**Data source:** World Bank Indicators API
https://api.worldbank.org/v2/country/UG/indicator/{code}
"""
import streamlit as st
import requests, duckdb, numpy as np, pandas as pd
import plotly.graph_objects as go
from statsmodels.tsa.arima.model import ARIMA

st.set_page_config(
    page_title="Uganda Economic Pulse",
    page_icon="🇺🇬",
    layout="wide"
)

st.title("Uganda Economic Pulse")
st.caption("Economic Monitoring, Risk Analysis & Growth Outlook")

IND = {
    "GDP Growth": "NY.GDP.MKTP.KD.ZG",
    "Inflation": "FP.CPI.TOTL.ZG",
    "Unemployment": "SL.UEM.TOTL.ZS",
    "Exports": "NE.EXP.GNFS.ZS",
    "Imports": "NE.IMP.GNFS.ZS",
    "Poverty": "SI.POV.DDAY"
}


@st.cache_data(ttl=3600)
def get_data():
    rows = []

        for name, code in IND.items():
        url = f"https://api.worldbank.org/v2/country/UGA/indicator/{code}"
        try:
            resp = requests.get(
                url, params={"format": "json", "per_page": 1000}, timeout=15
            )
            resp.raise_for_status()
            payload = resp.json()

            # World Bank quirk: a bad indicator/country still returns HTTP 200,
            # but with a 1-element array carrying an error message instead of
            # a [metadata, rows] pair. Guard against that before indexing [1].
            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                st.warning(f"No data returned for {name} ({code}) — skipping.")
                continue

            data = payload[1]
            rows += [
                {
                    "indicator": name,
                    "year": int(x["date"]),
                    "value": float(x["value"])
                }
                for x in data if x.get("value") is not None
            ]
        except requests.exceptions.RequestException as e:
            st.warning(f"Could not fetch {name}: {e}")
            continue

    df = pd.DataFrame(rows)

    con = duckdb.connect(":memory:")
    con.register("economic", df)

    return con.execute("""
        SELECT indicator, year, value
        FROM economic
        ORDER BY year
    """).df()


df = get_data()

trade = df[df.indicator.isin(["Exports", "Imports"])].pivot(
    index="year",
    columns="indicator",
    values="value"
).reset_index()

trade["Trade Balance"] = trade["Exports"] - trade["Imports"]

latest = (
    df.sort_values("year")
    .groupby("indicator")
    .tail(1)
    .set_index("indicator")["value"]
)


def risk(value, low, high, reverse=False):
    if reverse:
        return 0 if value >= high else 1 if value >= low else 2
    return 0 if value < low else 1 if value < high else 2


risk_scores = {
    "GDP Growth": risk(latest["GDP Growth"], 3, 5, True),
    "Inflation": risk(latest["Inflation"], 5, 8),
    "Unemployment": risk(latest["Unemployment"], 5, 8)
}

tb = trade["Trade Balance"].dropna().iloc[-1]
risk_scores["Trade"] = 0 if tb >= 0 else 1 if tb >= -5 else 2

overall = round(np.mean(list(risk_scores.values())) * 50, 1)
level = "Low" if overall <= 39 else "Moderate" if overall <= 69 else "High"


page = st.sidebar.radio(
    "Navigation",
    ["01 Economic Overview", "02 Indicators & Forecast"]
)


# =========================================================
# PAGE 1 — OVERVIEW
# =========================================================

if page == "01 Economic Overview":

    st.header("Economic Overview")
    st.write("What is happening in Uganda's economy?")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("GDP Growth", f"{latest['GDP Growth']:.1f}%")
    c2.metric("Inflation", f"{latest['Inflation']:.1f}%")
    c3.metric("Unemployment", f"{latest['Unemployment']:.1f}%")
    c4.metric("Trade Balance", f"{tb:.1f}%")

    st.subheader("Economic Trends")

    trend = df[df.indicator.isin(
        ["GDP Growth", "Inflation", "Unemployment"]
    )]

    fig = go.Figure()

    for indicator in trend.indicator.unique():
        x = trend[trend.indicator == indicator]
        fig.add_trace(go.Scatter(
            x=x.year,
            y=x.value,
            mode="lines+markers",
            name=indicator
        ))

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Percentage",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Overall Economic Risk")

    st.metric("Risk Level", f"{level} — {overall}/100")

    r1, r2, r3, r4 = st.columns(4)

    for col, (name, score) in zip(
        [r1, r2, r3, r4],
        risk_scores.items()
    ):
        col.metric(
            name,
            ["Low", "Moderate", "High"][score]
        )

    st.subheader("Data-informed priorities")

    if risk_scores["Inflation"] > 0:
        st.write("• Monitor inflationary pressure and price stability.")

    if risk_scores["GDP Growth"] > 0:
        st.write("• Support productivity and sustainable economic growth.")

    if risk_scores["Unemployment"] > 0:
        st.write("• Strengthen employment and skills-development opportunities.")

    if risk_scores["Trade"] > 0:
        st.write("• Monitor import pressure and trade-balance deterioration.")

    st.info(
        "This is an analytical risk framework developed for this project "
        "and is not an official World Bank or Government classification."
    )


# =========================================================
# PAGE 2 — INDICATORS & FORECAST
# =========================================================

else:

    st.header("Indicators & Forecast")
    st.write("Explore historical performance and forecast the selected indicator.")

    options = [
        "GDP Growth",
        "Inflation",
        "Unemployment",
        "Exports",
        "Imports",
        "Trade Balance",
        "Poverty"
    ]

    indicator = st.selectbox(
        "Select an indicator",
        options
    )

    horizon = st.slider(
        "Forecast horizon (years)",
        1, 3, 2
    )

    # Select data
    if indicator == "Trade Balance":
        data = trade[["year", "Trade Balance"]].rename(
            columns={"Trade Balance": "value"}
        )
    else:
        data = df[df.indicator == indicator][["year", "value"]].copy()

    data = data.dropna().sort_values("year")

    # Historical chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.year,
        y=data.value,
        mode="lines+markers",
        name="Historical"
    ))

    # Forecast
    forecastable = indicator != "Poverty"

    if forecastable and len(data) >= 8:

        series = data.set_index("year")["value"]

        try:
            model = ARIMA(series, order=(1, 1, 1)).fit()
            result = model.get_forecast(horizon)

            fc = result.predicted_mean
            ci = result.conf_int()

            years = list(
                range(
                    int(series.index.max()) + 1,
                    int(series.index.max()) + horizon + 1
                )
            )

            forecast_df = pd.DataFrame({
                "year": years,
                "forecast": fc.values,
                "lower": ci.iloc[:, 0].values,
                "upper": ci.iloc[:, 1].values
            })

            fig.add_trace(go.Scatter(
                x=forecast_df.year,
                y=forecast_df.forecast,
                mode="lines+markers",
                name="Forecast",
                line=dict(dash="dash")
            ))

            fig.add_trace(go.Scatter(
                x=list(forecast_df.year) +
                  list(forecast_df.year[::-1]),
                y=list(forecast_df.upper) +
                  list(forecast_df.lower[::-1]),
                fill="toself",
                line=dict(width=0),
                name="95% Prediction Interval"
            ))

        except Exception:
            forecast_df = None

    else:
        forecast_df = None

    fig.update_layout(
        title=f"{indicator}: Historical Trend & Forecast",
        xaxis_title="Year",
        yaxis_title="Value",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Statistics
    a, b, c, d = st.columns(4)

    a.metric("Latest", f"{data.value.iloc[-1]:.2f}")
    b.metric("Average", f"{data.value.mean():.2f}")
    c.metric("Maximum", f"{data.value.max():.2f}")
    d.metric("Minimum", f"{data.value.min():.2f}")

    if forecast_df is not None:

        st.subheader("Forecast")

        st.dataframe(
            forecast_df.rename(columns={
                "year": "Year",
                "forecast": "Forecast",
                "lower": "Lower 95%",
                "upper": "Upper 95%"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Forecasts are generated using ARIMA with 95% prediction intervals."
        )

    elif indicator == "Poverty":

        st.warning(
            "Poverty is not forecast because observations are irregular "
            "and primarily survey-based."
        )

    else:

        st.warning(
            "There are not enough observations to generate a reliable forecast."
        )

    st.subheader("Historical Data")

    st.dataframe(
        data.sort_values("year", ascending=False),
        use_container_width=True,
        hide_index=True
    )
