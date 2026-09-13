import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from google import genai
from pydantic import BaseModel, Field
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Surma River Basin | Flood Early Warning System",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROFESSIONAL CSS INJECTION ---
st.markdown("""
    <style>
    /* Dark Theme Canvas */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Header Card */
    .header-card {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    
    /* Alert Panel Styling */
    .alert-card-danger {
        background-color: #1a0f1a;
        border: 1px solid #991b1b;
        border-radius: 10px;
        padding: 20px;
    }
    
    .alert-card-normal {
        background-color: #062016;
        border: 1px solid #166534;
        border-radius: 10px;
        padding: 20px;
    }
    
    /* Hide Streamlit Header/Footer Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown("""
    <div class="header-card">
        <h1 style="margin:0; font-size: 28px; color: #f8fafc;">🌊 Surma River Basin — Flood Early Warning System</h1>
        <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">
            Real-Time Telemetry & AI Incident Dispatch System | Station: Sunamganj (25.0686° N, 91.4004° E)
        </p>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Monitoring Settings")
    auto_refresh = st.toggle("Enable Auto-Refresh", value=True)
    refresh_interval = st.slider("Polling Interval (seconds)", 10, 300, 30)
    st.divider()
    st.caption("System Status: Operational 🟢")

# --- DATA FETCHING (TELEMETRY) ---
@st.cache_data(ttl=300)
def fetch_telemetry():
    lat, lon = 25.0686, 91.4004
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}&daily=river_discharge&forecast_days=3"
    try:
        res = requests.get(url, timeout=10).json()
        daily = res.get("daily", {})
        df = pd.DataFrame({
            "Date": pd.to_datetime(daily.get("time", [])),
            "Discharge (m³/s)": daily.get("river_discharge", [])
        })
        return df, lat, lon
    except Exception:
        return pd.DataFrame(), lat, lon

df_telemetry, gauge_lat, gauge_lon = fetch_telemetry()

# --- KPI METRICS ROW ---
if not df_telemetry.empty:
    current_discharge = df_telemetry["Discharge (m³/s)"].iloc[0]
    peak_discharge = df_telemetry["Discharge (m³/s)"].max()
    threshold = 500.0
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Current Flow Rate", f"{current_discharge:.1f} m³/s")
    with m2:
        st.metric("3-Day Peak Discharge", f"{peak_discharge:.1f} m³/s")
    with m3:
        st.metric("Warning Threshold", f"{threshold:.0f} m³/s")
    with m4:
        status_label = "CRITICAL" if peak_discharge > threshold else "NORMAL"
        st.metric("Basin Alert Status", status_label)

st.divider()

# --- TWO-COLUMN MAIN CANVAS ---
col_map_chart, col_ai = st.columns([1.8, 1.2], gap="large")

with col_map_chart:
    st.subheader("📊 Discharge Forecast & Geospatial Mapping")
    
    if not df_telemetry.empty:
        st.line_chart(df_telemetry.set_index("Date"), height=220)
    
    map_data = pd.DataFrame([{"lat": gauge_lat, "lon": gauge_lon, "name": "Sunamganj Gauge"}])
    view_state = pdk.ViewState(latitude=gauge_lat, longitude=gauge_lon, zoom=10, pitch=45)
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_data,
        get_position=["lon", "lat"],
        get_color=[239, 68, 68, 200] if peak_discharge > threshold else [34, 197, 94, 200],
        get_radius=2000,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10"
    ))

with col_ai:
    st.subheader("🚨 Gemini Structured Incident Dispatch")
    
    class FloodAdvisory(BaseModel):
        risk_level: str = Field(description="LOW, MEDIUM, HIGH, or CRITICAL")
        advisory_bn: str = Field(description="Official emergency advisory in Bengali")
        advisory_en: str = Field(description="Official emergency advisory in English")
        recommended_actions: list[str] = Field(description="Key action items for local authorities")

    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    
    if api_key and not df_telemetry.empty:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Analyze Surma River discharge data: current {current_discharge} m3/s, peak {peak_discharge} m3/s against threshold {threshold} m3/s. Provide structured advisory."
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": FloodAdvisory,
                }
            )
            
            import json
            advisory_data = json.loads(response.text)
            card_class = "alert-card-danger" if advisory_data.get("risk_level") in ["HIGH", "CRITICAL"] else "alert-card-normal"
            
            st.markdown(f"""
                <div class="{card_class}">
                    <h3 style="margin-top:0; color:#38bdf8;">Risk Level: {advisory_data.get('risk_level')}</h3>
                    <p><strong>🇧🇩 বাংলা নির্দেশিকা:</strong><br>{advisory_data.get('advisory_bn')}</p>
                    <p><strong>🇬🇧 English Advisory:</strong><br>{advisory_data.get('advisory_en')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("#### Recommended Emergency Actions")
            for action in advisory_data.get("recommended_actions", []):
                st.markdown(f"* {action}")
                
        except Exception as e:
            st.warning("Telemetry processed. AI Dispatch temporarily unavailable.")
    else:
        st.info("Enter a valid GEMINI_API_KEY to enable AI dispatch generation.")
