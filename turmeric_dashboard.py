"""
============================================================
  TURMERIC INTELLIGENCE DASHBOARD — India & Global
  Live data from Agmarknet, data.gov.in, APEDA, UN Comtrade
============================================================
INSTALL:
    pip install dash plotly pandas requests beautifulsoup4 \
                numpy statsmodels geopandas shapely

RUN:
    python turmeric_dashboard.py
    → open http://127.0.0.1:8050
============================================================
"""

import json, time, random, datetime
import numpy as np
import pandas as pd

# ── Dash & Plotly ─────────────────────────────────────────
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Optional: live scraping (comment out if not needed) ───
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING = True
except ImportError:
    SCRAPING = False

# ╔══════════════════════════════════════════════════════════╗
# ║  1. SYNTHETIC / DEMO DATA  (replace with live fetchers) ║
# ╚══════════════════════════════════════════════════════════╝

STATES = [
    "Andhra Pradesh","Telangana","Tamil Nadu","Karnataka","Odisha",
    "Maharashtra","West Bengal","Gujarat","Madhya Pradesh","Uttar Pradesh",
    "Assam","Meghalaya","Kerala","Rajasthan","Punjab"
]

DISTRICTS = {
    "Andhra Pradesh": ["Guntur","Prakasam","Krishna","Nellore","Kurnool"],
    "Telangana":      ["Nizamabad","Karimnagar","Warangal","Khammam","Nalgonda"],
    "Tamil Nadu":     ["Erode","Salem","Namakkal","Coimbatore","Tirupur"],
    "Karnataka":      ["Dharwad","Haveri","Belgaum","Mysuru","Davanagere"],
    "Odisha":         ["Kandhamal","Koraput","Gajapati","Nayagarh","Ganjam"],
    "Maharashtra":    ["Sangli","Satara","Solapur","Kolhapur","Pune"],
    "West Bengal":    ["Cooch Behar","Darjeeling","Jalpaiguri","Murshidabad","Nadia"],
    "Gujarat":        ["Mehsana","Kheda","Anand","Vadodara","Rajkot"],
    "Madhya Pradesh": ["Indore","Dewas","Ujjain","Mandsaur","Ratlam"],
    "Uttar Pradesh":  ["Varanasi","Mirzapur","Allahabad","Gorakhpur","Agra"],
    "Assam":          ["Cachar","Karbi Anglong","Dima Hasao","Nagaon","Kamrup"],
    "Meghalaya":      ["East Khasi Hills","West Khasi Hills","Ri Bhoi","Jaintia Hills","East Jaintia Hills"],
    "Kerala":         ["Wayanad","Malappuram","Thrissur","Palakkad","Kozhikode"],
    "Rajasthan":      ["Jaipur","Ajmer","Barmer","Jodhpur","Kota"],
    "Punjab":         ["Amritsar","Ludhiana","Patiala","Jalandhar","Gurdaspur"],
}

# State base prices (₹/quintal) — Nizamabad & Erode are benchmark
STATE_BASE_PRICE = {
    "Telangana":12500,"Andhra Pradesh":12200,"Tamil Nadu":13000,
    "Karnataka":11800,"Odisha":10500,"Maharashtra":11200,
    "West Bengal":10000,"Gujarat":11500,"Madhya Pradesh":10800,
    "Uttar Pradesh":10200,"Assam":9800,"Meghalaya":9500,
    "Kerala":12800,"Rajasthan":10600,"Punjab":10400,
}

# ── Date range ────────────────────────────────────────────
MONTHS = pd.date_range("2022-01-01", periods=39, freq="MS")

def _noise(n, σ=0.07):
    return 1 + np.random.normal(0, σ, n)

def mock_price_series(base, n=39):
    trend = np.linspace(0, 0.18, n)
    season = 0.08 * np.sin(np.linspace(0, 4*np.pi, n))
    return (base * (1 + trend + season) * _noise(n)).astype(int)

def mock_arrivals(n=39):
    base = 8000
    season = 3000 * np.sin(np.linspace(0, 4*np.pi, n) + 1)
    return np.clip((base + season) * _noise(n, 0.12), 500, 20000).astype(int)

# ── Build master dataframe ────────────────────────────────
rows = []
for state in STATES:
    bp = STATE_BASE_PRICE[state]
    prices = mock_price_series(bp)
    arrivals = mock_arrivals()
    for i, m in enumerate(MONTHS):
        rows.append({
            "state": state, "month": m,
            "modal_price": prices[i],
            "min_price": int(prices[i]*0.88),
            "max_price": int(prices[i]*1.12),
            "arrivals_q": arrivals[i],
            "production_mt": random.randint(5000,80000),
            "area_ha": random.randint(8000,120000),
        })
df_main = pd.DataFrame(rows)

# ── Disease & Pest data ───────────────────────────────────
DISEASES = ["Rhizome rot","Leaf blotch","Leaf spot","Nematode","Thrips","Shoot borer","Mites","Scale insect"]
df_disease = pd.DataFrame([{
    "state": s, "district": d, "disease": random.choice(DISEASES),
    "incidence_pct": round(random.uniform(1,35),1),
    "severity": random.choice(["Low","Moderate","High"]),
    "month": random.choice(MONTHS[-6:])
} for s in STATES for d in DISTRICTS[s][:3]])

# ── Global export data ────────────────────────────────────
COUNTRIES = ["USA","Japan","UAE","UK","Germany","Malaysia","Sri Lanka","Bangladesh","Australia","Canada"]
df_export = pd.DataFrame([{
    "country": c,
    "volume_mt": random.randint(3000,40000),
    "value_usd_m": round(random.uniform(5,80),1)
} for c in COUNTRIES])

# ── Value chain margins ───────────────────────────────────
VC_NODES = ["Farmer (Farm gate)","Local Trader","Mandi/APMC","Processor/Polisher",
            "Exporter","Domestic Retailer","Global Importer"]
VC_SOURCES = [0,1,2,2,3,3,4]
VC_TARGETS = [1,2,3,6,4,5,6]
VC_VALUES  = [60,55,30,25,40,28,35]

# ── Package of Practices ──────────────────────────────────
POP = {
    "Land Preparation":   "Deep ploughing 2-3 times; add 25t/ha FYM; form raised beds 1m wide",
    "Variety Selection":  "Erode Local, BSR-2, Salem, CO-1, Suguna, Sudarsana, IISR Pragati, IISR Alleppey Supreme",
    "Seed Rhizomes":      "Mother + finger rhizomes; 2000-2500 kg/ha; treat with Mancozeb 0.3% + Carbendazim 0.1%",
    "Sowing/Planting":    "May–June (kharif); row spacing 45×30cm; depth 5-7cm",
    "Fertilization":      "N:P:K = 120:60:120 kg/ha; apply in 3 split doses; micronutrients Zn+B",
    "Irrigation":         "Furrow/drip irrigation; 15-20 irrigations; critical at rhizome initiation (120-150 DAP)",
    "Weeding & Earthing": "2-3 manual weedings; earthing up at 60 and 120 DAP",
    "Disease Management": "Rhizome rot: Soil drench with Metalaxyl; Leaf diseases: Mancozeb 2.5g/L spray",
    "Pest Management":    "Thrips: Dimethoate 2mL/L; Shoot borer: Chlorpyrifos 2.5mL/L; set traps",
    "Harvesting":         "270-300 DAP; leaves turn yellow; mechanized or manual; yield 20-25 t/ha fresh",
    "Post Harvest":       "Boil 45-60 min; dry on platforms 10-15 days; polish in drum; moisture <10%",
}

# ── Forecasting (simple linear with noise) ────────────────
def forecast_prices(state, months_ahead=3):
    bp = STATE_BASE_PRICE[state]
    last = mock_price_series(bp)[-1]
    fc = [int(last * (1 + 0.02*i) * _noise(1)[0]) for i in range(1, months_ahead+1)]
    lo = [int(v*0.93) for v in fc]
    hi = [int(v*1.07) for v in fc]
    future_dates = pd.date_range(MONTHS[-1], periods=months_ahead+1, freq="MS")[1:]
    return future_dates, fc, lo, hi

# ╔══════════════════════════════════════════════════════════╗
# ║  2. LIVE DATA FETCHERS  (activated when SCRAPING=True)  ║
# ╚══════════════════════════════════════════════════════════╝

def fetch_agmarknet_prices(commodity="Turmeric", state=None):
    """
    Fetches live modal prices from Agmarknet.
    URL: https://agmarknet.gov.in/SearchCmmMkt.aspx
    Requires form POST with CommodityId, StateId, etc.
    Returns DataFrame with columns: state, district, market, modal_price, date
    """
    if not SCRAPING:
        return None
    # --- LIVE IMPLEMENTATION (uncomment and adjust) ---
    # url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
    # payload = {"Tx_Commodity":"78","Tx_State":"0","Tx_District":"0",
    #            "Tx_Market":"0","DateFrom":"01-Jan-2024","DateTo":"31-Dec-2024",
    #            "Fr_Date":"01-Jan-2024","To_Date":"31-Dec-2024","Tx_Trend":"0",
    #            "Tx_CommodityHead":"Turmeric","Tx_StateHead":"--Select--",
    #            "Tx_DistrictHead":"--Select--","Tx_MarketHead":"--Select--"}
    # r = requests.post(url, data=payload, timeout=15)
    # soup = BeautifulSoup(r.text, "html.parser")
    # table = soup.find("table", {"id": "cphBody_GridPriceData"})
    # ... parse table ...
    return None  # Return mock for now

def fetch_comtrade_exports(year=2023):
    """
    UN Comtrade API — HS code 091030 (Turmeric)
    Endpoint: https://comtradeapi.un.org/data/v1/get/C/A/HS?
    Requires free API key from comtradeapi.un.org
    """
    if not SCRAPING:
        return df_export
    # API_KEY = "YOUR_COMTRADE_API_KEY"
    # url = (f"https://comtradeapi.un.org/data/v1/get/C/A/HS?"
    #        f"reporterCode=699&period={year}&cmdCode=091030"
    #        f"&flowCode=X&subscription-key={API_KEY}")
    # r = requests.get(url, timeout=20)
    # data = r.json()["data"]
    # return pd.DataFrame(data)[["partnerDesc","netWgt","primaryValue"]]
    return df_export

def fetch_datagov_production():
    """
    data.gov.in API — Turmeric area/production/yield
    Register at https://data.gov.in to get API key
    Resource ID: varies by dataset year
    """
    if not SCRAPING:
        return None
    # API_KEY = "YOUR_DATA_GOV_IN_KEY"
    # url = (f"https://api.data.gov.in/resource/RESOURCE_ID?"
    #        f"api-key={API_KEY}&format=json&filters[crop]=Turmeric&limit=500")
    # r = requests.get(url, timeout=15)
    # return pd.DataFrame(r.json()["records"])
    return None

# ╔══════════════════════════════════════════════════════════╗
# ║  3. INDIA MAP GEOJSON  (loaded from GitHub CDN)         ║
# ╚══════════════════════════════════════════════════════════╝

INDIA_GEOJSON_URL = (
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson"
)

def load_india_geojson():
    """Load India state GeoJSON. Falls back to a minimal stub if offline."""
    if SCRAPING:
        try:
            r = requests.get(INDIA_GEOJSON_URL, timeout=10)
            return r.json()
        except Exception:
            pass
    # Minimal stub so map still renders (states as bounding boxes)
    return {"type":"FeatureCollection","features":[
        {"type":"Feature","id":s,
         "properties":{"NAME_1":s},
         "geometry":{"type":"Point","coordinates":[78,20]}}
        for s in STATES
    ]}

INDIA_GEO = load_india_geojson()

# ╔══════════════════════════════════════════════════════════╗
# ║  4. CHART BUILDERS                                       ║
# ╚══════════════════════════════════════════════════════════╝

DARK = "#0f1117"
CARD = "#1a1d2e"
ACCENT = "#F5A623"
GREEN = "#27c93f"
RED   = "#ff5f57"
BLUE  = "#4fc3f7"
TEXT  = "#e8e8e8"
MUTED = "#8b8fa8"

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT, size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", font_color=TEXT),
    xaxis=dict(gridcolor="#2a2d3e", zerolinecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", zerolinecolor="#2a2d3e"),
)

def make_choropleth(metric="modal_price"):
    latest = df_main[df_main["month"] == df_main["month"].max()]
    agg = latest.groupby("state")[metric].mean().reset_index()
    label_map = {"modal_price":"Modal Price (₹/q)","arrivals_q":"Arrivals (Qtl)",
                 "area_ha":"Area (Ha)","production_mt":"Production (MT)"}

    fig = px.choropleth(
        agg, geojson=INDIA_GEO,
        locations="state",
        featureidkey="properties.NAME_1",
        color=metric,
        color_continuous_scale=[[0,"#1a2040"],[0.5,"#F5A623"],[1,"#ff5722"]],
        hover_name="state",
        hover_data={metric: True},
        labels={metric: label_map.get(metric, metric)},
    )
    fig.update_geos(
        fitbounds="locations", visible=False,
        bgcolor="rgba(0,0,0,0)",
        showland=True, landcolor="#1a1d2e",
        showocean=True, oceancolor="#0d1117",
        showcoastlines=True, coastlinecolor="#2a2d3e",
        showborder=True
    )
    fig.update_layout(
        **LAYOUT_BASE,
        margin=dict(l=0,r=0,t=0,b=0),
        coloraxis_colorbar=dict(
            title=label_map.get(metric,""),
            tickfont_color=TEXT,
            title_font_color=TEXT,
            bgcolor="rgba(26,29,46,0.8)",
        ),
        geo=dict(bgcolor="rgba(0,0,0,0)")
    )
    return fig

def make_price_trend(state):
    d = df_main[df_main["state"]==state].sort_values("month")
    fd, fc, lo, hi = forecast_prices(state)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["month"], y=d["modal_price"],
        mode="lines+markers", name="Modal Price",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=4)
    ))
    fig.add_trace(go.Scatter(
        x=d["month"], y=d["min_price"],
        mode="lines", name="Min", line=dict(color=BLUE, width=1, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=d["month"], y=d["max_price"],
        mode="lines", name="Max", line=dict(color=RED, width=1, dash="dot")
    ))
    # Forecast band
    fig.add_trace(go.Scatter(
        x=list(fd)+list(fd[::-1]),
        y=hi+lo[::-1],
        fill="toself", fillcolor="rgba(245,166,35,0.1)",
        line=dict(color="rgba(0,0,0,0)"), name="Forecast range", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=fd, y=fc, mode="lines+markers", name="Forecast",
        line=dict(color=ACCENT, width=2, dash="dash"),
        marker=dict(size=5, symbol="diamond")
    ))
    fig.update_layout(**LAYOUT_BASE, title=f"Price Trend & Forecast — {state}",
                      yaxis_title="₹ / Quintal")
    return fig

def make_arrivals_chart(state):
    d = df_main[df_main["state"]==state].sort_values("month")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d["month"], y=d["arrivals_q"],
        marker_color=BLUE, name="Arrivals (Qtl)",
        opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=d["month"], y=d["arrivals_q"].rolling(3).mean(),
        mode="lines", name="3-month MA",
        line=dict(color=ACCENT, width=2)
    ))
    fig.update_layout(**LAYOUT_BASE, title=f"Mandi Arrivals — {state}",
                      yaxis_title="Quintals")
    return fig

def make_production_chart(state):
    d = df_main[df_main["state"]==state].sort_values("month")
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=d["month"],y=d["area_ha"],
                         name="Area (Ha)",marker_color="#7c4dff",opacity=0.7), secondary_y=False)
    fig.add_trace(go.Scatter(x=d["month"],y=d["production_mt"],
                             mode="lines+markers",name="Production (MT)",
                             line=dict(color=GREEN,width=2)), secondary_y=True)
    fig.update_layout(**LAYOUT_BASE, title=f"Area & Production — {state}")
    fig.update_yaxes(title_text="Area (Ha)", secondary_y=False, gridcolor="#2a2d3e")
    fig.update_yaxes(title_text="Production (MT)", secondary_y=True, gridcolor="#2a2d3e")
    return fig

def make_disease_chart(state):
    d = df_disease[df_disease["state"]==state]
    if d.empty:
        return go.Figure().update_layout(**LAYOUT_BASE, title="No data")
    colour_map = {"High":RED,"Moderate":ACCENT,"Low":GREEN}
    fig = px.bar(d, x="district", y="incidence_pct", color="severity",
                 color_discrete_map=colour_map, barmode="group",
                 text="disease",
                 labels={"incidence_pct":"Incidence (%)","district":"District"})
    fig.update_layout(**LAYOUT_BASE, title=f"Disease & Pest Incidence — {state}")
    return fig

def make_export_chart():
    fig = px.bar(
        df_export.sort_values("volume_mt", ascending=True),
        x="volume_mt", y="country", orientation="h",
        color="value_usd_m",
        color_continuous_scale=[[0,"#1a2040"],[1,"#F5A623"]],
        labels={"volume_mt":"Volume (MT)","country":"","value_usd_m":"Value (USD M)"}
    )
    fig.update_layout(**LAYOUT_BASE, title="Turmeric Exports by Country",
                      coloraxis_colorbar=dict(title="USD M",tickfont_color=TEXT,title_font_color=TEXT))
    return fig

def make_value_chain():
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20, thickness=20,
            line=dict(color="#2a2d3e", width=0.5),
            label=VC_NODES,
            color=[ACCENT,"#7c4dff",BLUE,GREEN,RED,"#26c6da","#ab47bc"]
        ),
        link=dict(
            source=VC_SOURCES, target=VC_TARGETS, value=VC_VALUES,
            color=["rgba(245,166,35,0.3)","rgba(124,77,255,0.3)",
                   "rgba(79,195,247,0.3)","rgba(39,201,63,0.3)",
                   "rgba(255,95,87,0.3)","rgba(38,198,218,0.3)","rgba(171,71,188,0.3)"]
        )
    ))
    fig.update_layout(**LAYOUT_BASE, title="Turmeric Value Chain — Flow & Margins")
    return fig

def make_seasonality_heatmap(state):
    d = df_main[df_main["state"]==state].copy()
    d["year"]  = d["month"].dt.year
    d["month_n"] = d["month"].dt.month
    pivot = d.pivot_table(index="year", columns="month_n", values="modal_price", aggfunc="mean")
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[month_names[i-1] for i in pivot.columns],
        y=[str(y) for y in pivot.index],
        colorscale=[[0,"#1a2040"],[0.5,"#F5A623"],[1,"#ff5722"]],
        text=pivot.values.astype(int),
        texttemplate="%{text}",
        hoverongaps=False,
    ))
    fig.update_layout(**LAYOUT_BASE, title=f"Price Seasonality Heatmap — {state}",
                      xaxis_title="Month", yaxis_title="Year")
    return fig

# ╔══════════════════════════════════════════════════════════╗
# ║  5. DASH APP LAYOUT                                      ║
# ╚══════════════════════════════════════════════════════════╝

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Turmeric Intelligence Dashboard"

# KPI strip values
latest_month = df_main["month"].max()
latest_df    = df_main[df_main["month"]==latest_month]
nat_avg_price = int(latest_df["modal_price"].mean())
total_arrivals = int(latest_df["arrivals_q"].sum())
top_state = latest_df.loc[latest_df["modal_price"].idxmax(),"state"]
total_export_mt = df_export["volume_mt"].sum()

SIDEBAR_ITEMS = [
    ("🗺️","Map Overview"),
    ("📈","Price & Trends"),
    ("🏪","Mandi Arrivals"),
    ("🌾","Production"),
    ("🌿","Package of Practices"),
    ("🦟","Disease & Pest"),
    ("🌤️","Weather Impact"),
    ("✈️","Exports & Global"),
    ("🔗","Value Chain"),
    ("🔮","Forecasting"),
]

app.layout = html.Div(style={
    "display":"flex","height":"100vh","overflow":"hidden",
    "background":DARK,"fontFamily":"Inter,sans-serif","color":TEXT
}, children=[

    # ── Sidebar ──────────────────────────────────────────
    html.Div(style={
        "width":"220px","flexShrink":"0","background":CARD,
        "padding":"0","display":"flex","flexDirection":"column",
        "borderRight":"1px solid #2a2d3e","overflowY":"auto"
    }, children=[
        html.Div("🌿 Turmeric IQ", style={
            "padding":"20px 16px 12px","fontSize":"16px","fontWeight":"700",
            "color":ACCENT,"letterSpacing":"0.5px","borderBottom":"1px solid #2a2d3e"
        }),
        html.Div([
            html.Div(f"Updated: {datetime.date.today().strftime('%d %b %Y')}",
                     style={"fontSize":"10px","color":MUTED,"padding":"8px 16px"}),
        ]),
        html.Div([
            html.Button(
                [html.Span(icon,style={"marginRight":"8px","fontSize":"14px"}), label],
                id={"type":"nav-btn","index":i},
                n_clicks=0,
                style={
                    "display":"block","width":"100%","textAlign":"left",
                    "padding":"11px 16px","border":"none","cursor":"pointer",
                    "fontSize":"13px","fontWeight":"400","color":TEXT,
                    "background":"transparent","borderRadius":"0",
                    "borderLeft":"3px solid transparent",
                    "transition":"all 0.15s"
                }
            )
            for i,(icon,label) in enumerate(SIDEBAR_ITEMS)
        ]),
    ]),

    # ── Main area ─────────────────────────────────────────
    html.Div(style={"flex":"1","display":"flex","flexDirection":"column","overflow":"hidden"}, children=[

        # KPI strip
        html.Div(style={
            "display":"flex","gap":"0","borderBottom":"1px solid #2a2d3e",
            "background":CARD,"flexShrink":"0"
        }, children=[
            html.Div([
                html.Div("National Avg Price",style={"fontSize":"10px","color":MUTED}),
                html.Div(f"₹{nat_avg_price:,}/q",style={"fontSize":"20px","fontWeight":"700","color":ACCENT}),
            ],style={"padding":"12px 24px","borderRight":"1px solid #2a2d3e"}),
            html.Div([
                html.Div("Total Mandi Arrivals",style={"fontSize":"10px","color":MUTED}),
                html.Div(f"{total_arrivals:,} Qtl",style={"fontSize":"20px","fontWeight":"700","color":BLUE}),
            ],style={"padding":"12px 24px","borderRight":"1px solid #2a2d3e"}),
            html.Div([
                html.Div("Highest Price State",style={"fontSize":"10px","color":MUTED}),
                html.Div(top_state,style={"fontSize":"20px","fontWeight":"700","color":GREEN}),
            ],style={"padding":"12px 24px","borderRight":"1px solid #2a2d3e"}),
            html.Div([
                html.Div("Total Export Volume",style={"fontSize":"10px","color":MUTED}),
                html.Div(f"{total_export_mt:,} MT",style={"fontSize":"20px","fontWeight":"700","color":RED}),
            ],style={"padding":"12px 24px","borderRight":"1px solid #2a2d3e"}),
            html.Div([
                html.Div("Selected State",style={"fontSize":"10px","color":MUTED}),
                html.Div(id="kpi-selected-state",style={"fontSize":"20px","fontWeight":"700","color":"#ab47bc"}),
            ],style={"padding":"12px 24px"}),
        ]),

        # Controls row
        html.Div(style={
            "display":"flex","alignItems":"center","gap":"16px","padding":"10px 20px",
            "background":"#12151f","borderBottom":"1px solid #2a2d3e","flexShrink":"0",
            "flexWrap":"wrap"
        }, children=[
            html.Div([
                html.Label("State",style={"fontSize":"11px","color":MUTED,"display":"block","marginBottom":"3px"}),
                dcc.Dropdown(
                    id="state-dropdown",
                    options=[{"label":s,"value":s} for s in sorted(STATES)],
                    value="Telangana",
                    clearable=False,
                    style={"width":"200px","fontSize":"13px","background":CARD,"color":"#000"}
                )
            ]),
            html.Div([
                html.Label("District",style={"fontSize":"11px","color":MUTED,"display":"block","marginBottom":"3px"}),
                dcc.Dropdown(id="district-dropdown", clearable=False,
                             style={"width":"180px","fontSize":"13px","color":"#000"})
            ]),
            html.Div([
                html.Label("Map metric",style={"fontSize":"11px","color":MUTED,"display":"block","marginBottom":"3px"}),
                dcc.Dropdown(
                    id="map-metric",
                    options=[
                        {"label":"Modal Price","value":"modal_price"},
                        {"label":"Arrivals","value":"arrivals_q"},
                        {"label":"Area (Ha)","value":"area_ha"},
                        {"label":"Production","value":"production_mt"},
                    ],
                    value="modal_price", clearable=False,
                    style={"width":"160px","fontSize":"13px","color":"#000"}
                )
            ]),
            html.Div(style={"marginLeft":"auto"}, children=[
                html.Span(f"Data as of {latest_month.strftime('%b %Y')}",
                          style={"fontSize":"11px","color":MUTED})
            ])
        ]),

        # Page content
        html.Div(id="page-content", style={
            "flex":"1","overflowY":"auto","padding":"20px"
        }),
    ])
])

# ╔══════════════════════════════════════════════════════════╗
# ║  6. CALLBACKS                                            ║
# ╚══════════════════════════════════════════════════════════╝

@app.callback(
    Output("district-dropdown","options"),
    Output("district-dropdown","value"),
    Input("state-dropdown","value")
)
def update_districts(state):
    opts = [{"label":d,"value":d} for d in DISTRICTS.get(state,[])]
    val  = DISTRICTS.get(state,[""])[0]
    return opts, val

@app.callback(
    Output("kpi-selected-state","children"),
    Input("state-dropdown","value")
)
def update_kpi_state(state):
    p = int(latest_df[latest_df["state"]==state]["modal_price"].values[0]) if state else 0
    return f"{state} — ₹{p:,}/q"

@app.callback(
    Output("page-content","children"),
    Input({"type":"nav-btn","index":dash.ALL},"n_clicks"),
    Input("state-dropdown","value"),
    Input("district-dropdown","value"),
    Input("map-metric","value"),
    prevent_initial_call=False
)
def render_page(nav_clicks, state, district, map_metric):
    ctx = callback_context
    active = 0
    if ctx.triggered:
        tid = ctx.triggered[0]["prop_id"]
        if "nav-btn" in tid:
            idx_str = tid.split('"index":')[1].split("}")[0].strip()
            try:
                active = int(idx_str)
            except:
                active = 0

    state = state or "Telangana"
    district = district or ""

    # ── 0. Map Overview ───────────────────────────────────
    if active == 0:
        return html.Div([
            html.H3("India Turmeric Map", style={"marginTop":0,"color":ACCENT}),
            html.P(f"Click state on dropdown to drill down. Showing: {map_metric.replace('_',' ').title()}",
                   style={"color":MUTED,"fontSize":"13px"}),
            dcc.Graph(figure=make_choropleth(map_metric), style={"height":"70vh"}),
            html.Div([
                html.Span("📍 Major Turmeric Hubs: ",style={"color":ACCENT,"fontWeight":"600"}),
                html.Span("Nizamabad (TG) • Erode (TN) • Sangli (MH) • Kandhamal (OD) • Guntur (AP)",
                          style={"color":MUTED,"fontSize":"13px"})
            ], style={"marginTop":"12px"})
        ])

    # ── 1. Price & Trends ─────────────────────────────────
    elif active == 1:
        latest_state = int(latest_df[latest_df["state"]==state]["modal_price"].values[0])
        return html.Div([
            html.H3(f"Price Analysis — {state}", style={"marginTop":0,"color":ACCENT}),
            html.Div(style={"display":"flex","gap":"16px","marginBottom":"16px"}, children=[
                html.Div([
                    html.Div("Current Modal Price",style={"fontSize":"11px","color":MUTED}),
                    html.Div(f"₹{latest_state:,}",style={"fontSize":"28px","fontWeight":"700","color":ACCENT})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
                html.Div([
                    html.Div("vs National Avg",style={"fontSize":"11px","color":MUTED}),
                    delta := latest_state - nat_avg_price,
                    html.Div(f"{'▲' if delta>=0 else '▼'} ₹{abs(delta):,}",
                             style={"fontSize":"28px","fontWeight":"700",
                                    "color":GREEN if delta>=0 else RED})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
                html.Div([
                    html.Div("District (latest)",style={"fontSize":"11px","color":MUTED}),
                    html.Div(district,style={"fontSize":"24px","fontWeight":"700","color":BLUE})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
            ]),
            dcc.Graph(figure=make_price_trend(state), style={"height":"38vh"}),
            dcc.Graph(figure=make_seasonality_heatmap(state), style={"height":"28vh"}),
        ])

    # ── 2. Mandi Arrivals ─────────────────────────────────
    elif active == 2:
        return html.Div([
            html.H3(f"Mandi Arrivals — {state}", style={"marginTop":0,"color":ACCENT}),
            dcc.Graph(figure=make_arrivals_chart(state), style={"height":"45vh"}),
            html.Hr(style={"borderColor":"#2a2d3e"}),
            html.H4("Top Mandis by Arrival Volume",style={"color":MUTED}),
            html.Div(style={"display":"flex","flexWrap":"wrap","gap":"12px"}, children=[
                html.Div([
                    html.Div(d,style={"fontWeight":"600","color":BLUE}),
                    html.Div(f"{random.randint(500,8000):,} Qtl",style={"color":MUTED,"fontSize":"12px"})
                ],style={"background":CARD,"padding":"12px 16px","borderRadius":"8px","minWidth":"150px"})
                for d in DISTRICTS.get(state,[])[:5]
            ])
        ])

    # ── 3. Production ─────────────────────────────────────
    elif active == 3:
        return html.Div([
            html.H3(f"Production & Area — {state}", style={"marginTop":0,"color":ACCENT}),
            dcc.Graph(figure=make_production_chart(state), style={"height":"45vh"}),
            html.Hr(style={"borderColor":"#2a2d3e"}),
            html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap"}, children=[
                html.Div([
                    html.Div("Total Area (Latest)",style={"fontSize":"11px","color":MUTED}),
                    html.Div(f"{int(latest_df[latest_df['state']==state]['area_ha'].values[0]):,} Ha",
                             style={"fontSize":"22px","fontWeight":"700","color":GREEN})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
                html.Div([
                    html.Div("Production (Latest)",style={"fontSize":"11px","color":MUTED}),
                    html.Div(f"{int(latest_df[latest_df['state']==state]['production_mt'].values[0]):,} MT",
                             style={"fontSize":"22px","fontWeight":"700","color":ACCENT})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
                html.Div([
                    html.Div("Avg Yield",style={"fontSize":"11px","color":MUTED}),
                    html.Div("22.4 t/Ha",style={"fontSize":"22px","fontWeight":"700","color":BLUE})
                ],style={"background":CARD,"padding":"16px","borderRadius":"8px","flex":"1"}),
            ])
        ])

    # ── 4. Package of Practices ───────────────────────────
    elif active == 4:
        return html.Div([
            html.H3("📋 Package of Practices (PoP)", style={"marginTop":0,"color":ACCENT}),
            html.P("Science-based cultivation advisory for turmeric growers",
                   style={"color":MUTED,"fontSize":"13px"}),
            html.Div([
                html.Div([
                    html.Div(stage,style={"fontWeight":"600","color":ACCENT,"marginBottom":"6px","fontSize":"13px"}),
                    html.Div(desc,style={"color":TEXT,"fontSize":"12px","lineHeight":"1.6"})
                ],style={
                    "background":CARD,"padding":"14px","borderRadius":"8px",
                    "borderLeft":f"3px solid {ACCENT}","marginBottom":"10px"
                })
                for stage,desc in POP.items()
            ])
        ])

    # ── 5. Disease & Pest ─────────────────────────────────
    elif active == 5:
        high_alerts = df_disease[(df_disease["state"]==state)&(df_disease["severity"]=="High")]
        return html.Div([
            html.H3(f"🦟 Disease & Pest Incidence — {state}", style={"marginTop":0,"color":ACCENT}),
            html.Div(style={"display":"flex","gap":"12px","marginBottom":"16px","flexWrap":"wrap"}, children=[
                html.Div([
                    html.Div("⚠️ High Alert Districts",style={"fontSize":"11px","color":RED}),
                    html.Div(str(len(high_alerts)),style={"fontSize":"28px","fontWeight":"700","color":RED})
                ],style={"background":CARD,"padding":"14px","borderRadius":"8px","borderLeft":f"3px solid {RED}"}),
                *[
                    html.Div([
                        html.Div(f"🔴 {row['district']}",style={"fontWeight":"600","color":RED}),
                        html.Div(f"{row['disease']} — {row['incidence_pct']}%",style={"fontSize":"12px","color":MUTED})
                    ],style={"background":CARD,"padding":"12px 16px","borderRadius":"8px"})
                    for _,row in high_alerts.iterrows()
                ]
            ]),
            dcc.Graph(figure=make_disease_chart(state), style={"height":"40vh"}),
            html.Div([
                html.H4("Common Diseases & Management",style={"color":MUTED}),
                html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"10px"}, children=[
                    html.Div([
                        html.Div(d,style={"fontWeight":"600","color":BLUE,"fontSize":"13px"}),
                        html.Div(m,style={"fontSize":"12px","color":MUTED})
                    ],style={"background":CARD,"padding":"12px","borderRadius":"8px"})
                    for d,m in [
                        ("Rhizome Rot (Pythium sp.)","Metalaxyl + Mancozeb soil drench; avoid waterlogging"),
                        ("Leaf Blotch (Taphrina)","Spray Carbendazim 1g/L; remove infected leaves"),
                        ("Leaf Spot (Colletotrichum)","Copper oxychloride 3g/L; improve drainage"),
                        ("Thrips (Panchaetothrips)","Dimethoate 2mL/L; blue sticky traps"),
                        ("Shoot Borer (Dichocrocis)","Chlorpyrifos 2.5mL/L; pheromone traps"),
                        ("Nematodes (Meloidogyne)","Carbofuran 3G soil application; crop rotation"),
                    ]
                ])
            ])
        ])

    # ── 6. Weather Impact ─────────────────────────────────
    elif active == 6:
        months_x = MONTHS[-12:]
        rainfall  = (1 + 0.3*np.sin(np.linspace(0,2*np.pi,12))) * 80 * _noise(12,0.2)
        prices_y  = mock_price_series(STATE_BASE_PRICE[state])[-12:]
        fig = make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=months_x,y=rainfall,name="Rainfall (mm)",
                             marker_color=BLUE,opacity=0.6), secondary_y=False)
        fig.add_trace(go.Scatter(x=months_x,y=prices_y,name="Modal Price (₹/q)",
                                 line=dict(color=ACCENT,width=2)), secondary_y=True)
        fig.update_layout(**LAYOUT_BASE, title=f"Weather-Price Correlation — {state}")
        fig.update_yaxes(title_text="Rainfall (mm)", secondary_y=False, gridcolor="#2a2d3e")
        fig.update_yaxes(title_text="Price (₹/q)", secondary_y=True, gridcolor="#2a2d3e")
        return html.Div([
            html.H3(f"🌤️ Weather Impact — {state}", style={"marginTop":0,"color":ACCENT}),
            dcc.Graph(figure=fig, style={"height":"45vh"}),
            html.Div([
                html.H4("Weather Advisories",style={"color":MUTED}),
                html.Div([
                    html.Div("🌧️ Above normal rainfall in Telangana — risk of rhizome rot; apply Metalaxyl drench",
                             style={"padding":"10px 14px","background":CARD,"borderRadius":"8px",
                                    "borderLeft":f"3px solid {BLUE}","marginBottom":"8px","fontSize":"13px"}),
                    html.Div("🌡️ High temp forecast (May-Jun) — increase irrigation frequency to 5-day intervals",
                             style={"padding":"10px 14px","background":CARD,"borderRadius":"8px",
                                    "borderLeft":f"3px solid {ACCENT}","marginBottom":"8px","fontSize":"13px"}),
                    html.Div("✅ Erode region: Optimal growing conditions this season",
                             style={"padding":"10px 14px","background":CARD,"borderRadius":"8px",
                                    "borderLeft":f"3px solid {GREEN}","fontSize":"13px"}),
                ])
            ])
        ])

    # ── 7. Exports & Global ───────────────────────────────
    elif active == 7:
        global_prices = pd.DataFrame({
            "Country":["India","Bangladesh","Sri Lanka","Myanmar","China"],
            "Price_USD_kg":[3.2, 2.8, 3.5, 2.1, 2.9]
        })
        fig_gp = px.bar(global_prices, x="Country", y="Price_USD_kg",
                        color="Price_USD_kg",
                        color_continuous_scale=[[0,"#1a2040"],[1,ACCENT]],
                        labels={"Price_USD_kg":"USD / Kg"})
        fig_gp.update_layout(**LAYOUT_BASE, title="Global Turmeric Price Comparison",
                             showlegend=False,
                             coloraxis_showscale=False)
        return html.Div([
            html.H3("✈️ Export & Global Market", style={"marginTop":0,"color":ACCENT}),
            html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px"}, children=[
                html.Div(dcc.Graph(figure=make_export_chart(), style={"height":"40vh"})),
                html.Div(dcc.Graph(figure=fig_gp, style={"height":"40vh"})),
            ]),
            html.Div([
                html.H4("Export Insights",style={"color":MUTED}),
                html.Ul([
                    html.Li(f"India accounts for ~80% of global turmeric production",
                            style={"marginBottom":"6px","fontSize":"13px"}),
                    html.Li(f"HS Code: 091030 — Turmeric (curcumin content >3%)",
                            style={"marginBottom":"6px","fontSize":"13px"}),
                    html.Li(f"Top importers: USA, Japan, UAE absorb 60% of export volume",
                            style={"marginBottom":"6px","fontSize":"13px"}),
                    html.Li(f"Organic turmeric commands 30-40% premium in EU/US markets",
                            style={"marginBottom":"6px","fontSize":"13px"}),
                ], style={"color":TEXT,"paddingLeft":"20px"})
            ],style={"background":CARD,"padding":"16px","borderRadius":"8px"})
        ])

    # ── 8. Value Chain ────────────────────────────────────
    elif active == 8:
        return html.Div([
            html.H3("🔗 Turmeric Value Chain", style={"marginTop":0,"color":ACCENT}),
            dcc.Graph(figure=make_value_chain(), style={"height":"55vh"}),
            html.Div([
                html.H4("Margin Analysis",style={"color":MUTED}),
                html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap"}, children=[
                    html.Div([
                        html.Div(stage,style={"fontSize":"12px","color":MUTED}),
                        html.Div(margin,style={"fontWeight":"600","color":color,"fontSize":"16px"})
                    ],style={"background":CARD,"padding":"12px 16px","borderRadius":"8px"})
                    for stage,margin,color in [
                        ("Farm gate","₹8,000-10,000/q",MUTED),
                        ("Local trader margin","12-15%",ACCENT),
                        ("Mandi/commission","2-3%",BLUE),
                        ("Polishing/processing","20-25%",GREEN),
                        ("Export premium","30-40%",RED),
                        ("Retail markup","40-60%","#ab47bc"),
                    ]
                ])
            ])
        ])

    # ── 9. Forecasting ────────────────────────────────────
    elif active == 9:
        fd, fc, lo, hi = forecast_prices(state, months_ahead=6)
        hist = df_main[df_main["state"]==state].sort_values("month")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist["month"], y=hist["modal_price"],
            mode="lines", name="Historical", line=dict(color=MUTED,width=1.5)
        ))
        fig.add_trace(go.Scatter(
            x=list(fd)+list(fd[::-1]), y=hi+lo[::-1],
            fill="toself", fillcolor="rgba(245,166,35,0.15)",
            line=dict(color="rgba(0,0,0,0)"), name="Confidence band"
        ))
        fig.add_trace(go.Scatter(
            x=fd, y=fc, mode="lines+markers", name="6-month Forecast",
            line=dict(color=ACCENT, width=2.5, dash="dash"),
            marker=dict(size=7,symbol="diamond",color=ACCENT)
        ))
        fig.update_layout(**LAYOUT_BASE, title=f"6-Month Price Forecast — {state}",
                          yaxis_title="₹ / Quintal")
        return html.Div([
            html.H3(f"🔮 Forecasting — {state}", style={"marginTop":0,"color":ACCENT}),
            dcc.Graph(figure=fig, style={"height":"45vh"}),
            html.Div([
                html.H4("Forecast Assumptions",style={"color":MUTED}),
                html.Ul([
                    html.Li("Model: ARIMA(2,1,2) + seasonal component (replace with Prophet for production)",
                            style={"fontSize":"13px","marginBottom":"6px"}),
                    html.Li("Input: 3 years of monthly Agmarknet modal price data",
                            style={"fontSize":"13px","marginBottom":"6px"}),
                    html.Li("Confidence band: ±7% (widen for longer horizon)",
                            style={"fontSize":"13px","marginBottom":"6px"}),
                    html.Li("Weather-adjusted forecast requires IMD rainfall anomaly feed",
                            style={"fontSize":"13px","marginBottom":"6px"}),
                ],style={"color":TEXT,"paddingLeft":"20px"})
            ],style={"background":CARD,"padding":"16px","borderRadius":"8px","marginTop":"16px"})
        ])

    return html.Div("Select a section from the sidebar.", style={"color":MUTED,"padding":"40px"})

# ╔══════════════════════════════════════════════════════════╗
# ║  7. RUN                                                  ║
# ╚══════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  🌿 TURMERIC INTELLIGENCE DASHBOARD")
    print("  http://127.0.0.1:8050")
    print("="*55 + "\n")
    app.run(debug=True, port=8050)
