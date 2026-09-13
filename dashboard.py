import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import requests
from google import genai
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime

# ==========================================
# 1. PAGE CONFIG & GOOGLE DESIGN SYSTEM
# ==========================================
st.set_page_config(
    page_title="Surma River Basin | Operational Flood Command",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Glassmorphism & Material 3 Styling Injection
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Google Sans', sans-serif;
        }
        
        .stApp {
            background-color: #060911;
            background-image: radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.05) 0px, transparent 50%),
                              radial-gradient(at 100% 100%, rgba(239, 68, 68, 0.05) 0px, transparent 50%);
            color: #f1f5f9;
        }

        /* Glassmorphism Cards */
        .glass-card {
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            margin-bottom: 20px;
        }

        /* Metric Typography Override */
        [data-testid="stMetricValue"] {
            font-family: 'Google Sans', sans-serif;
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #38bdf8 !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8 !important;
        }

        /* Status Badges */
        .status-badge-critical {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 6px 16px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            display: inline-block;
        }

        .status-badge-normal {
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid #22c55e;
            color: #86efac;
            padding: 6px 16px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            display: inline-block;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BRANDED COMMAND HEADER
# ==========================================
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="background: linear-gradient(135deg, #0284c7, #2563eb); padding: 12px; border-radius: 12px;">
                <span style="font-size: 28px;">🌊</span>
            </div>
            <div>
                <h1 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #f8fafc;">Surma Basin Operational Warning Center</h1>
                <p style="margin: 2px 0 0 0; color: #64748b; font-size: 0.9rem;">
                    Sunamganj Hydrological Station (25.0686° N, 91.4004° E) | Open-Meteo & Gemini Flash Pipeline
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.markdown(f"""
        <div style="text-align: right; background: rgba(15, 23, 42, 0.4); padding: 10px 16px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05);">
            <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">System Latency</div>
            <div style="font-family: 'Roboto Mono', monospace; font-size: 1.1rem; color: #38bdf8; font-weight: 500;">
                LIVE TELEMETRY
            </div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 3. TELEMETRY PIPELINE & DATA PROCESSING
# ==========================================
LAT, LON = 25.0686, 91.4004
CRITICAL_THRESHOLD = 500.0  # m3/s

@st.cache_data(ttl=300)
def load_telemetry_data():
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={LAT}&longitude={LON}&daily=river_discharge&forecast_days=7"
    try:
        res = requests.get(url, timeout=10).json()
        daily = res.get("daily", {})
        df = pd.DataFrame({
            "Timestamp": pd.to_datetime(daily.get("time", [])),
            "Discharge": daily.get("river_discharge", [])
        })
        df['Date_Label'] = df['Timestamp'].dt.strftime('%b %d')
        return df
    except Exception:
        return pd.DataFrame()

df_telemetry = load_telemetry_data()

# ==========================================
# 4. EXECUTIVE SUMMARY (METRIC ROW)
# ==========================================
if not df_telemetry.empty:
    current_flow = df_telemetry["Discharge"].iloc[0]
    peak_flow = df_telemetry["Discharge"].max()
    is_critical = peak_flow > CRITICAL_THRESHOLD

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Real-Time Flow", f"{current_flow:.1f} m³/s")
    with m2:
        st.metric("7-Day Forecast Peak", f"{peak_flow:.1f} m³/s")
    with m3:
        st.metric("Danger Threshold", f"{CRITICAL_THRESHOLD:.0f} m³/s")
    with m4:
        badge_html = f'<span class="status-badge-critical">🚨 CRITICAL RISK</span>' if is_critical else f'<span class="status-badge-normal">🟢 NOMINAL</span>'
        st.markdown(f"""
            <div style="padding-top: 8px;">
                <div style="font-size: 0.85rem; text-transform: uppercase; color: #94a3b8; margin-bottom: 8px;">Operational State</div>
                {badge_html}
            </div>
        """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 5. ASYMMETRIC ANALYTICS GRID
# ==========================================
grid_left, grid_right = st.columns([1.7, 1.3], gap="large")

with grid_left:
    st.subheader("📊 Streamflow Dynamics & Geospatial Context")
    
    # 5.1 Altair Gradient Hydrograph
    if not df_telemetry.empty:
        chart = alt.Chart(df_telemetry).mark_area(
            line={'color': '#38bdf8', 'size': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='rgba(56, 189, 248, 0.0)', offset=0),
                       alt.GradientStop(color='rgba(56, 189, 248, 0.35)', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('Date_Label:O', title='Forecast Date', axis=alt.Axis(labelAngle=0, labelColor='#94a3b8')),
            y=alt.Y('Discharge:Q', title='Discharge (m³/s)', axis=alt.Axis(labelColor='#94a3b8')),
            tooltip=['Date_Label', alt.Tooltip('Discharge', format='.1f')]
        ).properties(height=240)

        # Danger Threshold Overlay Line
        threshold_line = alt.Chart(pd.DataFrame({'y': [CRITICAL_THRESHOLD]})).mark_rule(
            color='#ef4444',
            strokeDash=[4, 4],
            size=1.5
        ).encode(y='y:Q')

        st.altair_chart(chart + threshold_line, use_container_width=True)

    # 5.2 PyDeck Dark Vector Map
    map_df = pd.DataFrame([{"lat": LAT, "lon": LON, "name": "Sunamganj Station"}])
    view_state = pdk.ViewState(latitude=LAT, longitude=LON, zoom=10, pitch=45)
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position=["lon", "lat"],
        get_color=[239, 68, 68, 220] if is_critical else [34, 197, 94, 220],
        get_radius=2500,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10"
    ), height=240)

with grid_right:
    st.subheader("🚨 Gemini Operational Incident Dispatch")
    
    # AI Output Schema Definition
    class OperationalAdvisory(BaseModel):
        risk_level: str = Field(description="LOW, MODERATE, HIGH, or CRITICAL")
        advisory_bn: str = Field(description="Bengali executive summary for local response teams")
        advisory_en: str = Field(description="English executive summary for agency coordination")
        protocols: list[str] = Field(description="Actionable 1-2 sentence operational directives")

    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    
    if api_key and not df_telemetry.empty:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Analyze Surma River discharge: current {current_flow:.1f} m3/s, 7-day peak {peak_flow:.1f} m3/s, threshold {CRITICAL_THRESHOLD:.0f} m3/s. Formulate precise operational advisory."
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": OperationalAdvisory,
                }
            )
            
            data = json.loads(response.text)
            risk = data.get("risk_level", "UNKNOWN")
            risk_color = "#ef4444" if risk in ["HIGH", "CRITICAL"] else "#38bdf8"

            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.8); border-left: 4px solid {risk_color}; padding: 18px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Assessed Threat Level</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: {risk_color};">{risk}</div>
                </div>
            """, unsafe_allow_html=True)

            tab_bn, tab_en = st.tabs(["🇧🇩 বাংলা নির্দেশিকা", "🇬🇧 English Advisory"])
            with tab_bn:
                st.markdown(f"<p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>{data.get('advisory_bn')}</p>", unsafe_allow_html=True)
            with tab_en:
                st.markdown(f"<p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>{data.get('advisory_en')}</p>", unsafe_allow_html=True)

            st.write("#### Response Directives")
            for idx, action in enumerate(data.get("protocols", [])):
                st.markdown(f"""
                    <div style="display: flex; align-items: flex-start; gap: 12px; background: rgba(30, 41, 59, 0.4); padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                        <span style="color: #38bdf8; font-family: 'Roboto Mono', monospace; font-weight: 700;">0{idx+1}</span>
                        <span style="color: #e2e8f0; font-size: 0.9rem;">{action}</span>
                    </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.warning("Telemetry active. AI Dispatch engine initializing...")
    else:
        st.info("Set GEMINI_API_KEY in Streamlit Secrets to activate live operational dispatch generation.")
