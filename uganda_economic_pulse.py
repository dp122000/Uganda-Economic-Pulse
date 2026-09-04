# -*- coding: utf-8 -*-
"""Uganda Economic Pulse_Capstone Project

**Economic Monitoring, Risk Analysis & Growth Outlook**

Uganda Economic Pulse is a data-driven economic intelligence dashboard designed to monitor Uganda’s economic performance, identify emerging risks and assess the near-term growth outlook. Using automated public data ingestion, SQL analytics, interactive visualizations, risk scoring and GDP forecasting.

The dashboard transforms key economic indicators into actionable insights for understanding Uganda’s changing economic landscape.

**Data source:** World Bank Indicators API
https://api.worldbank.org/v2/country/UG/indicator/{CODE}?format=json
"""
import streamlit as st
import requests, duckdb, numpy as np, pandas as pd
import plotly.express as px
from statsmodels.tsa.arima.model import ARIMA

st.set_page_config(
    page_title="Uganda Economic Pulse",
    page_icon="🇺🇬",
    layout="wide"
)

st.title("🇺🇬 Uganda Economic Pulse")
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
        data = requests.get(
            url, params={"format": "json", "per_page": 1000}
        ).json()[1]

        rows += [
            {
                "indicator": name,
                "year": int(x["date"]),
                "value": float(x["value"])
            }
            for x in data if x["value"] is not None
        ]

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
    index="year", columns="indicator", values="value"
).reset_index()

trade["Trade Balance"] = trade["Exports"] - trade["Imports"]

latest = df.sort_values("year").groupby("indicator").tail(1)
latest = latest.set_index("indicator")["value"]


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
    ["01 Overview", "02 Indicators", "03 Outlook & Risk"]
)


# ───────────────── OVERVIEW ─────────────────

if page == "01 Overview":

    st.header("What is happening?")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("GDP Growth", f"{latest['GDP Growth']:.1f}%")
    c2.metric("Inflation", f"{latest['Inflation']:.1f}%")
    c3.metric("Unemployment", f"{latest['Unemployment']:.1f}%")
    c4.metric("Trade Balance", f"{tb:.1f}%")

    st.subheader("Economic Trends")

    trend = df[df.indicator.isin(
        ["GDP Growth", "Inflation", "Unemployment"]
    )]

    fig = px.line(
        trend,
        x="year",
        y="value",
        color="indicator",
        markers=True,
        labels={"value": "Percentage", "year": "Year"}
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info(
        f"Current analytical economic risk: **{level}** "
        f"({overall}/100)."
    )

    st.caption(
        "Risk score is an analytical framework developed for this project "
        "and is not an official World Bank or Government classification."
    )


# ───────────────── INDICATORS ─────────────────

elif page == "02 Indicators":

    st.header("Why is it happening?")

    indicator = st.selectbox(
        "Select indicator",
        list(IND.keys())
    )

    data = df[df.indicator == indicator]

    fig = px.line(
        data,
        x="year",
        y="value",
        markers=True,
        title=indicator
    )

    st.plotly_chart(fig, use_container_width=True)

    a, b, c, d = st.columns(4)

    a.metric("Latest", f"{data.value.iloc[-1]:.2f}")
    b.metric("Average", f"{data.value.mean():.2f}")
    c.metric("Maximum", f"{data.value.max():.2f}")
    d.metric("Minimum", f"{data.value.min():.2f}")

    if indicator == "Trade Balance":
        st.dataframe(trade, use_container_width=True)
    else:
        st.dataframe(
            data.sort_values("year", ascending=False),
            use_container_width=True
        )

    if indicator == "Poverty":
        st.caption(
            "Poverty observations are survey-based and irregular. "
            "They are therefore not forecast."
        )


# ───────────────── OUTLOOK ─────────────────

else:

    st.header("What could happen next?")

    horizon = st.slider("Forecast horizon (years)", 1, 3, 3)

    gdp = df[df.indicator == "GDP Growth"].sort_values("year")
    series = gdp.set_index("year")["value"]

    model = ARIMA(series, order=(1, 1, 1)).fit()
    result = model.get_forecast(horizon)

    fc = result.predicted_mean
    ci = result.conf_int()

    years = list(range(series.index.max() + 1,
                       series.index.max() + horizon + 1))

    forecast_df = pd.DataFrame({
        "Year": years,
        "Forecast": fc.values,
        "Lower": ci.iloc[:, 0].values,
        "Upper": ci.iloc[:, 1].values
    })

    fig = px.line(
        forecast_df,
        x="Year",
        y="Forecast",
        markers=True,
        title="Uganda GDP Growth Forecast"
    )

    fig.add_scatter(
        x=forecast_df["Year"],
        y=forecast_df["Upper"],
        mode="lines",
        name="Upper 95% bound"
    )

    fig.add_scatter(
        x=forecast_df["Year"],
        y=forecast_df["Lower"],
        mode="lines",
        name="Lower 95% bound"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(forecast_df, use_container_width=True)

    st.subheader("Risk Assessment")

    st.metric("Overall Economic Risk", f"{level} — {overall}/100")

    for name, score in risk_scores.items():
        label = ["Low", "Moderate", "High"][score]
        st.write(f"**{name}:** {label}")

    st.subheader("Data-informed priorities")

    if risk_scores["Inflation"] > 0:
        st.write("• Monitor inflationary pressure and price stability.")

    if risk_scores["GDP Growth"] > 0:
        st.write("• Support productivity and sustainable economic growth.")

    if risk_scores["Unemployment"] > 0:
        st.write("• Strengthen employment and skills-development opportunities.")

    if risk_scores["Trade"] > 0:
        st.write("• Monitor import pressure and trade-balance deterioration.")

    st.caption(
        "GDP forecasts use an ARIMA model with 95% prediction intervals."
    )
