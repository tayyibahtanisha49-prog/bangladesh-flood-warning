import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import plotly.express as px
import requests
from google import genai
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime

# ==========================================
# 1. PAGE CORE & Google Material UI Styling
# ==========================================
st.set_page_config(
    page_title="Operational Flood Insight • Surma Basin",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Material Design aesthetics and layout spacing
st.markdown("""
    <style>
        /* Google Fonts Integration */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Google+Sans:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        
        h1, h2, h3, h4, .stMetric {
            font-family: 'Google Sans', sans-serif;
        }

        /* Material UI Dark Theme overrides */
        .stApp {
            background-color: #121212;
            color: #E0E0E0;
        }

        /* Structured Metric Card */
        [data-testid="stMetricValue"] {
            font-size: 2.8rem;
            font-weight: 500;
            color: #8AB4F8; /* Google Blue */
        }
        [data-testid="stMetricLabel"] {
            font-size: 1rem;
            color: #9AA0A6;
        }
        
        /* Analysis Containers (Cards) */
        .analysis-card {
            background-color: #1E1E1E;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.3), 0 1px 3px 1px rgba(0,0,0,0.15);
            margin-bottom: 16px;
            border: 1px solid #333;
        }
        
        /* Section Subheaders */
        .section-header {
            color: #E8EAED;
            font-weight: 500;
            margin-bottom: 20px;
            font-size: 1.2rem;
            letter-spacing: 0.5px;
        }
        
        /* Alert Status Pill */
        .status-pill {
            padding: 6px 16px;
            border-radius: 100px;
            font-weight: 500;
            font-size: 0.85rem;
            display: inline-block;
        }

        /* Main structure spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. APPLICATION HEADER (Google Minimalist)
# ==========================================
h_col1, h_col2 = st.columns([4, 1])

with h_col1:
    st.markdown('<div style="display:flex; align-items:center;">', unsafe_allow_html=True)
    st.image("https://www.gstatic.com/images/branding/product/2x/disaster_relief_flood_56dp.png", width=48) # Flood specific icon
    st.markdown("""
        <div style="margin-left: 16px;">
            <h1 style="margin:0; font-size: 2.2rem; font-weight: 400; color: #E8EAED;">Surma Basin Flood Analyst</h1>
            <p style="margin: 0; color: #9AA0A6; font-size: 1rem;">Sunamganj Operational Centre | Active Monitoring 🟢</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with h_col2:
    st.markdown(f"""
        <div style="text-align: right; color: #9AA0A6;">
            <p style="margin:0; font-size:0.9rem;">Last Synced (UTC)</p>
            <p style="margin:0; font-weight:500; color:#E8EAED; font-size:1.1rem;">{datetime.utcnow().strftime('%H:%M:%S')}</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 3. GLOBAL TELEMETRY (Structured Data Fetch)
# ==========================================
# Define Station Metadata
stations = {
    "Sunamganj": {"lat": 25.0686, "lon": 91.4004, "basins": "Surma", "id": "SN001"},
}
selected_station_name = "Sunamganj"
station_data = stations[selected_station_name]

# Define critical discharge threshold
THRESHOLD_CRITICAL = 500.0  # m3/s

@st.cache_data(ttl=300)
def fetch_telemetry(lat, lon):
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}&daily=river_discharge&forecast_days=7&timezone=UTC"
    try:
        res = requests.get(url, timeout=10).json()
        daily = res.get("daily", {})
        df = pd.DataFrame({
            "Timestamp": pd.to_datetime(daily.get("time", [])),
            "Discharge (m³/s)": daily.get("river_discharge", [])
        })
        
        # Calculate derived features
        df['Forecast_Day'] = df['Timestamp'].dt.strftime('%a, %b %d')
        df['Below_Threshold'] = df['Discharge (m³/s)'] < THRESHOLD_CRITICAL
        
        return df
    except Exception as e:
        st.error(f"Error connecting to Open-Meteo API. Check connectivity.")
        return pd.DataFrame()

# Initialize primary data
df_telemetry = fetch_telemetry(station_data['lat'], station_data['lon'])

# ==========================================
# 4. PRIMARY INTELLIGENCE: Executive Summary & KPIs
# ==========================================
with st.container():
    if not df_telemetry.empty:
        # Calculate derived analysis
        peak_discharge_m3 = df_telemetry["Discharge (m³/s)"].max()
        current_discharge_m3 = df_telemetry["Discharge (m³/s)"].iloc[0]
        critical_risk_flag = peak_discharge_m3 > THRESHOLD_CRITICAL
        
        # Structure KPI Row
        st.markdown('<p class="section-header">Executive Summary</p>', unsafe_allow_html=True)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([1, 1, 1, 1.5])
        
        with kpi_col1:
            st.metric("Current Streamflow", f"{current_discharge_m3:.1f}", help="Latest available telemetry.")
        
        with kpi_col2:
            st.metric("Forecasted Peak Discharge", f"{peak_discharge_m3:.1f}", help="Maximum discharge predicted in the next 7 days.")
        
        with kpi_col3:
            st.metric("Critical Action Threshold", f"{THRESHOLD_CRITICAL:.0f}", help="Discharge rate indicating major operational risk.")

        with kpi_col4:
            # Dynamic Status Pill
            status_text = "CRITICAL RISK ACTIVE" if critical_risk_flag else "NOMINAL MONITORING"
            status_color = "#EA4335" if critical_risk_flag else "#34A853" # Google Red / Green
            text_color = "white"
            
            st.markdown(f"""
                <div style="text-align: right; padding-top: 10px;">
                    <span class="status-pill" style="background-color: {status_color}; color: {text_color};">
                        {status_text}
                    </span>
                    <p style="margin: 8px 0 0 0; color: #9AA0A6; font-size: 0.9rem;">
                        Analysing telemetry for Basin ID: {station_data['basins']}
                    </p>
                </div>
            """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 5. SPATIAL & TEMPORAL ANALYSIS CONTAINER
# ==========================================
ana_col_map, ana_col_chart = st.columns([1.5, 2.5], gap="large")

# -- 5.1 Professional Geospatial Context --
with ana_col_map:
    st.markdown('<p class="section-header">Station Location & Spatial Risk</p>', unsafe_allow_html=True)
    
    # Map Styling (Google-like Dark Grey)
    view_state = pdk.ViewState(
        latitude=station_data['lat'],
        longitude=station_data['lon'],
        zoom=11,
        pitch=0
    )
    
    # Dynamic point coloring
    map_color = [234, 67, 53, 200] if critical_risk_flag else [52, 168, 83, 200] # Red or Green

    gauge_layer = pdk.Layer(
        "ScatterplotLayer",
        pd.DataFrame([station_data]),
        get_position=["lon", "lat"],
        get_radius=1000,
        get_color=map_color,
        pickable=True,
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10", # Clean professional basemap
        initial_view_state=view_state,
        layers=[gauge_layer],
        tooltip={"text": "Sunamganj Gauge\nLat: {lat}\nLon: {lon}"}
    ))

# -- 5.2 Advanced Temporal Forecast (Altair Chart) --
with ana_col_chart:
    st.markdown('<p class="section-header">7-Day Hydrological Forecast</p>', unsafe_allow_html=True)
    
    if not df_telemetry.empty:
        # Define Altair Chart for professional data viz
        chart = alt.Chart(df_telemetry).mark_area(
            line={'color':'#8AB4F8'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#202124', offset=0),
                       alt.GradientStop(color='#8AB4F8', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            ),
            opacity=0.3
        ).encode(
            x=alt.X('Forecast_Day:O', title='Date (UTC)'),
            y=alt.Y('Discharge (m³/s):Q', title='River Discharge (m³/s)'),
            tooltip=['Forecast_Day', alt.Tooltip('Discharge (m³/s)', format='.1f')]
        ).properties(height=300)

        # Add Critical Threshold Line
        rule = alt.Chart(pd.DataFrame({'y': [THRESHOLD_CRITICAL]})).mark_rule(
            color='#EA4335',
            strokeDash=[5, 5],
            size=2
        ).encode(y='y:Q')
        
        # Combine layers and display
        st.altair_chart(chart + rule, use_container_width=True)

st.divider()

# ==========================================
# 6. AI INCIDENT DISPATCH CONTAINER (Professional)
# ==========================================
st.markdown('<p class="section-header">🚨 Gemini Operations Briefing</p>', unsafe_allow_html=True)

# Google AI Schema Definition
class operationalBriefing(BaseModel):
    risk_assessment: str = Field(description="High-level assessment: LOW, MODERATE, HIGH, EXTREME")
    operational_impact_bn: str = Field(description="Analysis of local operational impact in Bengali")
    operational_impact_en: str = Field(description="Analysis of local operational impact in English")
    key_action_protocols: list[str] = Field(description="Structured emergency action protocols for response teams")

# API Configuration
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

with st.container():
    if api_key and not df_telemetry.empty:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Operational analysis of Surma river telemetry at Sunamganj. Current streamflow: {current_discharge_m3:.1f} m3/s, 7-day peak forecasted: {peak_discharge_m3:.1f} m3/s, critical threshold: {THRESHOLD_CRITICAL:.0f} m3/s. Provide structured response."
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": operationalBriefing,
                }
            )
            
            # Process AI output
            briefing = json.loads(response.text)
            
            ai_b_col1, ai_b_col2 = st.columns([1, 1.5], gap="large")
            
            # Left: Assessment & Bilingual Text
            with ai_b_col1:
                risk_level = briefing.get('risk_assessment')
                risk_color = "#EA4335" if risk_level in ["HIGH", "EXTREME"] else "#FBBC04" if risk_level == "MODERATE" else "#34A853"
                
                # Risk Assessment Block
                st.markdown(f"""
                    <div style="background-color: #1E1E1E; padding: 20px; border-radius: 8px; border-left: 5px solid {risk_color}; margin-bottom: 20px;">
                        <p style="margin:0; color: {risk_color}; font-weight: 500; font-size: 0.9rem;">Operations Risk Assessment</p>
                        <h3 style="margin: 4px 0 0 0; color: #E8EAED; font-size: 1.8rem;">{risk_level}</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # Bilingual Operational Impact Cards
                tab_bn, tab_en = st.tabs(["বাংলা ব্রিফিং (BN)", "English Briefing (EN)"])
                with tab_bn:
                    st.markdown(f'<p style="color: #9AA0A6; line-height: 1.6;">{briefing.get("operational_impact_bn")}</p>', unsafe_allow_html=True)
                with tab_en:
                    st.markdown(f'<p style="color: #9AA0A6; line-height: 1.6;">{briefing.get("operational_impact_en")}</p>', unsafe_allow_html=True)

            # Right: Action Protocols
            with ai_b_col2:
                st.markdown('<p style="color: #E8EAED; font-weight: 500; font-size: 1rem;">Action Protocols & Response Checklists</p>', unsafe_allow_html=True)
                for i, protocol in enumerate(briefing.get("key_action_protocols", [])):
                    # Material UI Checkbox aesthetic
                    st.markdown(f"""
                        <div style="display:flex; align-items:center; background-color: #252525; padding: 12px; border-radius: 4px; margin-bottom: 10px; border: 1px solid #333;">
                            <div style="width: 20px; height: 20px; border: 2px solid #8AB4F8; border-radius: 2px; margin-right: 12px; display: flex; align-items: center; justify-content: center; color: #8AB4F8; font-weight: 700;">{i+1}</div>
                            <p style="margin:0; color: #E8EAED; font-size: 0.95rem;">{protocol}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"Telemetry processed. Gemini AI Services temporarily unavailable.")
    elif not api_key:
        st.info("💡 A valid Gemini API Key is required in Streamlit Secrets (`GEMINI_API_KEY`) to enable the AI Incident Dispatch panel.")
    else:
        st.warning("Insufficient telemetry data to trigger Gemini AI briefing.")

# ==========================================
# 7. Operational Sidebar & Controls
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; margin-bottom: 20px;">
            <img src="https://www.gstatic.com/images/branding/product/2x/disaster_relief_flood_56dp.png" width="32">
            <h2 style="margin-left: 12px; font-weight: 400; color: #E8EAED;">Monitor Settings</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.caption(f"Connected to Station ID: {station_data['id']}")
    st.caption(f"Coordinates: {station_data['lat']}°N, {station_data['lon']}°E")
