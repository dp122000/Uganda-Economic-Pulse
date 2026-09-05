# 🇺🇬 Uganda Economic Pulse

### Economic Monitoring, Risk Analysis & Growth Outlook

Uganda Economic Pulse is an interactive economic intelligence dashboard that monitors Uganda’s key economic indicators, identifies emerging risks, and provides a short-term GDP growth outlook.

The dashboard uses automated data ingestion from the **World Bank API**, **DuckDB** for analytical queries, **Python** for data processing and forecasting, and **Streamlit + Plotly** for interactive visualization.


**Data source:** World Bank Indicators API 
https://api.worldbank.org/v2/country/UGA/indicator/{code}

### Key Indicators

* GDP Growth
* Inflation
* Unemployment
* Exports & Imports
* Trade Balance
* Poverty

### Key Features

* Automated public-data ingestion
* SQL-based analytical queries
* Interactive economic trend visualization
* Three-level economic risk assessment
* GDP growth forecasting with 95% prediction intervals
* Data-driven economic insights

### Tech Stack

**Python · Pandas · DuckDB · SQL · ARIMA · Plotly · Streamlit · World Bank API**

> **Note:** World Bank macroeconomic indicators are generally reported annually. The dashboard therefore provides automated and dynamically refreshed economic monitoring rather than real-time economic data.

This satisfies all four capstone requirements:
  1. Automated Data Ingestion  -> background thread syncs from the live
     World Bank API on a schedule and appends to a local CSV
  2. In-Memory Analytical Queries -> DuckDB SQL over the ingested table
  3. Visual Uncertainty Forecasts -> historical trend + forecast +
     widening confidence band, per indicator
  4. Live Public Deployment -> deploy this file via Streamlit Community Cloud

Run locally with:
    streamlit run app.py

### Project Purpose

To transform publicly available economic data into clear, accessible and actionable insights for understanding Uganda’s economic performance and outlook.
