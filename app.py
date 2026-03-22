import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
from datetime import datetime, timedelta
import time

# Optional ML
from statsmodels.tsa.arima.model import ARIMA

st.set_page_config(layout="wide")

st.title("🌾 TURMERIC COMMODITY INTELLIGENCE DASHBOARD")

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("Filters")

state = st.sidebar.selectbox("Select State", ["All", "Telangana", "Tamil Nadu", "Karnataka", "Maharashtra"])
days = st.sidebar.slider("Days of Data", 7, 120, 30)

# ================================
# DATA FETCH FUNCTIONS
# ================================

@st.cache_data(ttl=3600)
def fetch_agmarknet_data():
    try:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": "YOUR_API_KEY",
            "format": "json",
            "limit": 1000
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['records'])
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_weather():
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M,PRECTOT",
        "community": "AG",
        "longitude": 78.5,
        "latitude": 17.3,
        "start": "20240101",
        "end": "20241231",
        "format": "JSON"
    }
    r = requests.get(url, params=params)
    return r.json()

# ================================
# LOAD DATA
# ================================

df = fetch_agmarknet_data()

if df.empty:
    st.warning("⚠️ Data not loading. Add API key.")
else:
    df['modal_price'] = pd.to_numeric(df['modal_price'], errors='coerce')
    df = df.dropna()

# ================================
# MARKET MODULE
# ================================

st.header("📊 Market Intelligence")

if not df.empty:
    fig = px.line(df.head(days), y="modal_price", title="Price Trend")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df.head(50))

# ================================
# PRODUCTION MODULE (STATIC ICAR DATA)
# ================================

st.header("🌱 Production & Package of Practices")

st.markdown("""
**Source: ICAR-IISR, TNAU, KAU**

- Temperature: 20–35°C  
- Rainfall: ~1500 mm  
- Seed rate: 2500 kg rhizomes/ha  
- Irrigation: 7–10 days interval  
- Harvest: 7–9 months  

### Fertilizer
- NPK: 75:50:50 kg/ha

### Varieties
- Lakadong
- Rajendra Sonia
""")

# ================================
# PEST & DISEASE MODULE
# ================================

st.header("🐛 Pest & Disease Management")

st.markdown("""
**Source: ICAR-IISR, PPQS, TNAU**

### Major Pests:
- Shoot Borer → Dry shoots  
- Thrips → Leaf discoloration  

### Management:
- Neem oil spray  
- Biological control (Bacillus)

### Diseases:
- Leaf blotch → Brown spots  
- Rhizome rot  

### Control:
- Crop rotation  
- Fungicide treatment  
""")

# ================================
# WEATHER MODULE
# ================================

st.header("🌦 Climate Analysis")

weather = fetch_weather()

try:
    temp = weather['properties']['parameter']['T2M']
    df_temp = pd.DataFrame(temp.items(), columns=["date", "temp"])
    fig2 = px.line(df_temp, x="date", y="temp", title="Temperature Trend")
    st.plotly_chart(fig2, use_container_width=True)
except:
    st.warning("Weather data not available")

# ================================
# FORECASTING MODULE
# ================================

st.header("📈 Price Forecast")

if not df.empty:
    try:
        series = df['modal_price'].head(50)
        model = ARIMA(series, order=(2,1,2))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=10)

        fig3 = px.line(y=forecast, title="10-Day Forecast")
        st.plotly_chart(fig3, use_container_width=True)
    except:
        st.warning("Forecasting failed")

# ================================
# DECISION SUPPORT
# ================================

st.header("💡 Decision Support")

if not df.empty:
    latest_price = df['modal_price'].iloc[0]

    if latest_price > df['modal_price'].mean():
        st.success("📈 Price above average → Consider selling")
    else:
        st.warning("📉 Price below average → Consider storing")

# ================================
# DOWNLOAD
# ================================

st.header("⬇️ Download Data")

if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "turmeric_data.csv")

# ================================
# FOOTER
# ================================

st.markdown("""
---
**Data Sources:**  
AGMARKNET | data.gov.in | ICAR | TNAU | NASA POWER | FAO  
""")