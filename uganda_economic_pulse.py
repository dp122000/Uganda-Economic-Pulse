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
st.caption("Turning Uganda’s economic data into evidence for better understanding, monitoring and decision-making.")

IND = {
    "GDP Growth": "NY.GDP.MKTP.KD.ZG",
    "Inflation": "FP.CPI.TOTL.ZG",
    "Unemployment": "SL.UEM.TOTL.ZS",
    "Exports": "NE.EXP.GNFS.ZS",
    "Imports": "NE.IMP.GNFS.ZS",
    "Poverty": "SI.POV.DDAY"
}

@st.cache_data(ttl=3600)
def load_data():
    rows = []

    for name, code in IND.items():
        url = f"https://api.worldbank.org/v2/country/UGA/indicator/{code}"
        r = requests.get(
            url,
            params={"format": "json", "per_page": 1000},
            timeout=30
        )
        data = r.json()[1]

        rows += [
            {"indicator": name, "year": int(x["date"]),
             "value": float(x["value"])}
            for x in data if x["value"] is not None
        ]

    df = pd.DataFrame(rows)

    con = duckdb.connect(":memory:")
    con.register("data", df)

    return con.execute("""
        SELECT indicator, year, value
        FROM data
        ORDER BY year
    """).df()


df = load_data()

trade = (
    df[df.indicator.isin(["Exports", "Imports"])]
    .pivot(index="year", columns="indicator", values="value")
    .reset_index()
)

trade["Trade Balance"] = trade["Exports"] - trade["Imports"]

latest = (
    df.sort_values("year")
    .groupby("indicator")
    .tail(1)
    .set_index("indicator")["value"]
)

trade_latest = trade["Trade Balance"].dropna().iloc[-1]


def risk(v, low, high, reverse=False):
    if reverse:
        return 0 if v >= high else 1 if v >= low else 2
    return 0 if v < low else 1 if v < high else 2


risks = {
    "GDP Growth": risk(latest["GDP Growth"], 3, 5, True),
    "Inflation": risk(latest["Inflation"], 5, 8),
    "Unemployment": risk(latest["Unemployment"], 5, 8),
    "Trade": 0 if trade_latest >= 0 else 1 if trade_latest >= -5 else 2
}

overall = round(np.mean(list(risks.values())) * 50, 1)
risk_level = "Low" if overall <= 33 else "Moderate" if overall <= 66 else "High"

page = st.sidebar.radio(
    "Dashboard",
    ["01 Home", "02 Indicators & Outlook"]
)

# =========================
# PAGE 1 — HOME
# =========================

if page == "01 Home":

    st.header("Economic Overview")
    st.write("What is happening in Uganda's economy?")

    a, b, c, d = st.columns(4)

    a.metric("GDP Growth", f"{latest['GDP Growth']:.1f}%")
    b.metric("Inflation", f"{latest['Inflation']:.1f}%")
    c.metric("Unemployment", f"{latest['Unemployment']:.1f}%")
    d.metric("Trade Balance", f"{trade_latest:.1f}%")

    st.subheader("Economic Trends")

    selected = st.multiselect(
        "Indicators to compare",
        ["GDP Growth", "Inflation", "Unemployment"],
        default=["GDP Growth", "Inflation"]
    )

    if selected:
        trend = df[df.indicator.isin(selected)]

        fig = go.Figure()

        for indicator in selected:
            x = trend[trend.indicator == indicator]
            fig.add_trace(go.Scatter(
                x=x.year,
                y=x.value,
                mode="lines+markers",
                name=indicator
            ))

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Value",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Economic Risk")

    st.metric(
        "Overall Analytical Risk",
        f"{risk_level} — {overall}/100"
    )

    r1, r2, r3, r4 = st.columns(4)

    r1.write(f"**GDP Growth:** {'Low' if risks['GDP Growth']==0 else 'Moderate' if risks['GDP Growth']==1 else 'High'}")
    r2.write(f"**Inflation:** {'Low' if risks['Inflation']==0 else 'Moderate' if risks['Inflation']==1 else 'High'}")
    r3.write(f"**Unemployment:** {'Low' if risks['Unemployment']==0 else 'Moderate' if risks['Unemployment']==1 else 'High'}")
    r4.write(f"**Trade:** {'Low' if risks['Trade']==0 else 'Moderate' if risks['Trade']==1 else 'High'}")

    st.info(
        "Risk score is an analytical framework developed for this project "
        "and is not an official World Bank or Government classification."
    )


# =========================
# PAGE 2 — INDICATORS
# =========================

else:

    st.header("Indicators & Outlook")
    st.write("Explore an individual indicator and its projected outlook.")

    indicator = st.selectbox(
        "Select economic indicator",
        ["GDP Growth", "Inflation", "Unemployment",
         "Exports", "Imports", "Trade Balance", "Poverty"]
    )

    horizon = st.slider(
        "Forecast horizon",
        min_value=1,
        max_value=3,
        value=2
    )

    # Trade balance is derived
    if indicator == "Trade Balance":
        data = trade[["year", "Trade Balance"]].dropna()
        data.columns = ["year", "value"]
    else:
        data = df[df.indicator == indicator][["year", "value"]]

    data = data.sort_values("year")

    latest_value = data.value.iloc[-1]

    x1, x2, x3, x4 = st.columns(4)

    x1.metric("Latest", f"{latest_value:.2f}")
    x2.metric("Average", f"{data.value.mean():.2f}")
    x3.metric("Maximum", f"{data.value.max():.2f}")
    x4.metric("Minimum", f"{data.value.min():.2f}")

    st.subheader(f"{indicator} — Historical & Forecast")

    # Poverty has irregular survey observations
    if indicator == "Poverty":
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data.year,
            y=data.value,
            mode="lines+markers",
            name="Historical"
        ))

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Value",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.warning(
            "Poverty is not forecast because observations are irregular "
            "and primarily survey-based."
        )

    else:
        series = data.set_index("year")["value"]

        try:
            model = ARIMA(series, order=(1, 1, 1)).fit()
            result = model.get_forecast(horizon)

            forecast = result.predicted_mean
            interval = result.conf_int()

            years = range(
                series.index.max() + 1,
                series.index.max() + horizon + 1
            )

            fig = go.Figure()

            # Historical
            fig.add_trace(go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines+markers",
                name="Historical"
            ))

            # Forecast
            fig.add_trace(go.Scatter(
                x=list(years),
                y=forecast.values,
                mode="lines+markers",
                name="Forecast",
                line=dict(dash="dash")
            ))

            # Confidence interval
            fig.add_trace(go.Scatter(
                x=list(years) + list(years)[::-1],
                y=list(interval.iloc[:, 1]) +
                  list(interval.iloc[:, 0])[::-1],
                fill="toself",
                line=dict(width=0),
                name="95% Prediction Interval",
                opacity=0.25
            ))

            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Value",
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)

            forecast_table = pd.DataFrame({
                "Year": list(years),
                "Forecast": forecast.values,
                "Lower 95%": interval.iloc[:, 0].values,
                "Upper 95%": interval.iloc[:, 1].values
            })

            st.subheader("Forecast Values")
            st.dataframe(
                forecast_table,
                use_container_width=True,
                hide_index=True
            )

        except Exception:
            st.error(
                "There are not enough observations to produce a reliable "
                "forecast for this indicator."
            )

    st.subheader("Historical Data")

    st.dataframe(
        data.sort_values("year", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Forecasts are statistical estimates and should not be interpreted "
        "as official economic projections."
    )
