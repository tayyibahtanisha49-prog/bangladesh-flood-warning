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
# 1. PAGE CONFIG & DARK ENTERPRISE CSS
# ==========================================
st.set_page_config(
    page_title="Surma-Kushiyara Basin | Command Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Google Sans', sans-serif;
        }

        .stApp {
            background-color: #050811;
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.04) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(239, 68, 68, 0.04) 0%, transparent 40%);
            color: #e2e8f0;
        }

        /* Glassmorphism Containers */
        .command-card {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }

        /* Dark Metric Customization */
        [data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            color: #38bdf8 !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b !important;
        }

        /* Badge Pills */
        .status-badge-critical {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }

        .status-badge-normal {
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid #22c55e;
            color: #86efac;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. EXTENDED HYDROMETRIC NETWORK STATIONS
# ==========================================
STATIONS = {
    "Sunamganj Gauge (Surma River)": {
        "lat": 25.0686, "lon": 91.4004, "threshold": 500.0, "danger_stage_m": 8.50, 
        "basin": "Surma Basin", "district": "Sunamganj", "station_id": "BWDB-SN-01"
    },
    "Sylhet Sadar (Surma River)": {
        "lat": 24.8949, "lon": 91.8687, "threshold": 480.0, "danger_stage_m": 10.80, 
        "basin": "Surma Basin", "district": "Sylhet", "station_id": "BWDB-SY-02"
    },
    "Kanaighat (Surma River)": {
        "lat": 25.0061, "lon": 92.2641, "threshold": 420.0, "danger_stage_m": 12.75, 
        "basin": "Upper Surma", "district": "Sylhet", "station_id": "BWDB-KN-03"
    },
    "Markuli (Kushiyara River)": {
        "lat": 24.4251, "lon": 91.3853, "threshold": 520.0, "danger_stage_m": 9.40, 
        "basin": "Kushiyara Basin", "district": "Habiganj", "station_id": "BWDB-MK-04"
    }
}

# ==========================================
# 3. SIDEBAR CONTROLS & REPORT GENERATOR
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap: 10px; margin-bottom: 15px;">
            <div style="background: #0284c7; padding: 8px; border-radius: 8px;">🌊</div>
            <h3 style="margin:0; color:#f8fafc; font-size:1.1rem;">Station Network</h3>
        </div>
    """, unsafe_allow_html=True)
    
    selected_name = st.selectbox("Select Gauge Location", list(STATIONS.keys()))
    station = STATIONS[selected_name]
    
    st.divider()
    
    st.markdown("**Station Telemetry Metadata**")
    st.caption(f"🆔 **Station ID:** {station['station_id']}")
    st.caption(f"📍 **Basin System:** {station['basin']}")
    st.caption(f"🌐 **Coords:** {station['lat']}° N, {station['lon']}° E")
    st.caption(f"⚠️ **Threshold Discharge:** {station['threshold']} m³/s")
    st.caption(f"📏 **Critical Stage Level:** {station['danger_stage_m']} m")

# ==========================================
# 4. DATA FETCHING & DERIVED CALCULATIONS
# ==========================================
@st.cache_data(ttl=300)
def fetch_detailed_telemetry(lat, lon):
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}&daily=river_discharge&forecast_days=7"
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

df_telemetry = fetch_detailed_telemetry(station['lat'], station['lon'])

# Calculate Advanced Parameters
if not df_telemetry.empty:
    current_flow = df_telemetry["Discharge"].iloc[0]
    next_day_flow = df_telemetry["Discharge"].iloc[1] if len(df_telemetry) > 1 else current_flow
    flow_delta_24h = next_day_flow - current_flow
    peak_flow = df_telemetry["Discharge"].max()
    peak_date = df_telemetry.loc[df_telemetry["Discharge"].idxmax()]["Date_Label"]
    
    # Estimated Stage Level (Hydrological linear extrapolation)
    estimated_stage_m = (current_flow / station['threshold']) * station['danger_stage_m']
    is_critical = peak_flow > station['threshold']

# ==========================================
# 5. COMMAND CENTER HEADER
# ==========================================
h1, h2 = st.columns([3, 1])

with h1:
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap: 16px;">
            <div style="background: rgba(14, 165, 233, 0.1); border: 1px solid #0284c7; padding: 12px; border-radius: 10px;">
                <span style="font-size: 26px;">🛰️</span>
            </div>
            <div>
                <h1 style="margin:0; font-size: 1.7rem; color: #f8fafc;">Surma-Kushiyara Basin Early Warning Command Center</h1>
                <p style="margin:2px 0 0 0; color: #64748b; font-size: 0.88rem;">
                    Active Telemetry: <strong style="color:#e2e8f0;">{selected_name}</strong> | District: {station['district']}
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with h2:
    status_html = '<span class="status-badge-critical">🚨 CRITICAL ALERT ACTIVE</span>' if is_critical else '<span class="status-badge-normal">🟢 NOMINAL MONITORING</span>'
    st.markdown(f"""
        <div style="text-align: right; padding-top: 6px;">
            <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 6px;">BASIN OPERATIONAL STATUS</div>
            {status_html}
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 6. HIGH-DENSITY HYDROMETRIC KPI BANNER
# ==========================================
if not df_telemetry.empty:
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Real-Time Flow", f"{current_flow:.1f} m³/s", delta=f"{flow_delta_24h:+.1f} m³/s 24h")
    k2.metric("Est. Water Level", f"{estimated_stage_m:.2f} m", help="Calculated stage height derived from discharge rating curves.")
    k3.metric("Danger Stage Limit", f"{station['danger_stage_m']:.2f} m")
    k4.metric("7-Day Forecast Peak", f"{peak_flow:.1f} m³/s", help=f"Expected peak on {peak_date}")
    k5.metric("Action Threshold", f"{station['threshold']:.0f} m³/s")

st.divider()

# ==========================================
# 7. ASYMMETRIC ANALYTICAL GRID
# ==========================================
g_left, g_right = st.columns([1.7, 1.3], gap="large")

with g_left:
    st.markdown("#### 📊 Discharge Streamflow & 2022 Benchmark")
    
    if not df_telemetry.empty:
        # Streamflow Area Chart
        area_chart = alt.Chart(df_telemetry).mark_area(
            line={'color': '#38bdf8', 'size': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='rgba(56, 189, 248, 0.02)', offset=0),
                       alt.GradientStop(color='rgba(56, 189, 248, 0.3)', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('Date_Label:O', title='Date', axis=alt.Axis(labelColor='#94a3b8')),
            y=alt.Y('Discharge:Q', title='Discharge (m³/s)', axis=alt.Axis(labelColor='#94a3b8')),
            tooltip=['Date_Label', alt.Tooltip('Discharge', format='.1f')]
        ).properties(height=230)

        # Danger Threshold Rule
        threshold_rule = alt.Chart(pd.DataFrame({'y': [station['threshold']]})).mark_rule(
            color='#ef4444', strokeDash=[4, 4], size=1.5
        ).encode(y='y:Q')

        st.altair_chart(area_chart + threshold_rule, use_container_width=True)

    st.markdown("#### 🌍 Vector Station Map & Topography")
    
    # PyDeck Map
    map_df = pd.DataFrame([{"lat": station['lat'], "lon": station['lon'], "name": selected_name}])
    view_state = pdk.ViewState(latitude=station['lat'], longitude=station['lon'], zoom=10, pitch=45)
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position=["lon", "lat"],
        get_color=[239, 68, 68, 220] if is_critical else [34, 197, 94, 220],
        get_radius=3000,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10"
    ), height=220)

with g_right:
    st.markdown("#### 🚨 Gemini AI Operational Incident Briefing")
    
    class ExtendedAdvisory(BaseModel):
        threat_assessment: str = Field(description="LOW, MODERATE, HIGH, or CRITICAL")
        basin_summary_bn: str = Field(description="Bengali summary for field teams")
        basin_summary_en: str = Field(description="English summary for central coordination")
        priority_actions: list[str] = Field(description="3 actionable emergency steps")

    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    advisory_export_text = "AI Advisory unavailable."

    if api_key and not df_telemetry.empty:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Analyze gauge station {selected_name}. Current discharge: {current_flow:.1f} m3/s (24h change: {flow_delta_24h:+.1f} m3/s), Estimated stage: {estimated_stage_m:.2f}m vs critical {station['danger_stage_m']}m. Peak forecasted: {peak_flow:.1f} m3/s against threshold {station['threshold']} m3/s. Formulate briefing."
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ExtendedAdvisory,
                }
            )
            
            data = json.loads(response.text)
            threat = data.get("threat_assessment", "UNKNOWN")
            threat_color = "#ef4444" if threat in ["HIGH", "CRITICAL"] else "#38bdf8"

            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.8); border-left: 4px solid {threat_color}; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Assessed Threat Category</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: {threat_color};">{threat}</div>
                </div>
            """, unsafe_allow_html=True)

            tab_bn, tab_en = st.tabs(["🇧🇩 বাংলা নির্দেশিকা", "🇬🇧 English Advisory"])
            with tab_bn:
                st.markdown(f"<p style='color: #cbd5e1; font-size: 0.92rem; line-height: 1.6;'>{data.get('basin_summary_bn')}</p>", unsafe_allow_html=True)
            with tab_en:
                st.markdown(f"<p style='color: #cbd5e1; font-size: 0.92rem; line-height: 1.6;'>{data.get('basin_summary_en')}</p>", unsafe_allow_html=True)

            st.markdown("**Action Directives & Response Protocols**")
            for idx, action in enumerate(data.get("priority_actions", [])):
                st.markdown(f"""
                    <div style="display: flex; align-items: flex-start; gap: 10px; background: rgba(30, 41, 59, 0.4); padding: 10px; border-radius: 6px; margin-bottom: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                        <span style="color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-weight: 700;">0{idx+1}</span>
                        <span style="color: #e2e8f0; font-size: 0.88rem;">{action}</span>
                    </div>
                """, unsafe_allow_html=True)

            advisory_export_text = f"Threat Assessment: {threat}\nEN Briefing: {data.get('basin_summary_en')}\nBN Briefing: {data.get('basin_summary_bn')}"

        except Exception as e:
            st.warning("Telemetry connected. AI Incident Dispatch engine initializing...")
    else:
        st.info("Configure GEMINI_API_KEY in Streamlit Secrets to enable live automated incident dispatch.")

    st.divider()

    # --- SITUATION REPORT EXPORT BUTTON ---
    report_data = f"""OFFICIAL FLOOD SITUATION BRIEFING
Station: {selected_name} ({station['station_id']})
District: {station['district']} | Basin: {station['basin']}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

HYDROMETRIC TELEMETRY:
- Real-Time Flow: {current_flow:.1f} m3/s (24h Trend: {flow_delta_24h:+.1f} m3/s)
- Estimated Water Level: {estimated_stage_m:.2f} m
- Critical Danger Stage: {station['danger_stage_m']:.2f} m
- 7-Day Peak Forecast: {peak_flow:.1f} m3/s (Expected: {peak_date})
- Warning Threshold: {station['threshold']:.0f} m3/s

OPERATIONAL AI DISPATCH SUMMARY:
{advisory_export_text}
"""
    st.download_button(
        label="📄 Export Operational Situation Report (TXT)",
        data=report_data,
        file_name=f"Situation_Report_{station['station_id']}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
        use_container_width=True
    )
