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

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Surma-Kushiyara Basin | Flood Early Warning System",
    page_icon="🌊",
    layout="wide"
)

# --- MULTI-STATION DATABASE ---
STATIONS = {
    "Sunamganj (Surma River)": {"lat": 25.0686, "lon": 91.4004, "threshold": 500.0, "hist_peak": 850.0},
    "Sylhet Sadar (Surma River)": {"lat": 24.8949, "lon": 91.8687, "threshold": 480.0, "hist_peak": 790.0},
    "Kanaighat (Surma River)": {"lat": 25.0061, "lon": 92.2641, "threshold": 420.0, "hist_peak": 710.0},
    "Markuli (Kushiyara River)": {"lat": 24.4251, "lon": 91.3853, "threshold": 520.0, "hist_peak": 890.0}
}

# --- SIDEBAR: MULTI-STATION SELECTOR & EXPORT ---
with st.sidebar:
    st.header("⚙️ Station Selection")
    selected_station = st.selectbox("Choose Gauge Station", list(STATIONS.keys()))
    station = STATIONS[selected_station]
    
    st.divider()
    st.caption(f"Coordinates: {station['lat']}° N, {station['lon']}° E")
    st.caption(f"Danger Level: {station['threshold']} m³/s")

# --- DATA FETCHING ENGINE ---
@st.cache_data(ttl=300)
def fetch_telemetry(lat, lon):
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}&daily=river_discharge&forecast_days=7"
    try:
        res = requests.get(url, timeout=10).json()
        daily = res.get("daily", {})
        df = pd.DataFrame({
            "Timestamp": pd.to_datetime(daily.get("time", [])),
            "Discharge": daily.get("river_discharge", [])
        })
        df['Date_Label'] = df['Timestamp'].dt.strftime('%b %d')
        # Simulate historical baseline comparison
        df['2022_Flood_Peak'] = station['hist_peak']
        return df
    except Exception:
        return pd.DataFrame()

df_telemetry = fetch_telemetry(station['lat'], station['lon'])

# --- MAIN TITLE & METRICS ---
st.title(f"🌊 Operational Warning System — {selected_station}")

if not df_telemetry.empty:
    current_flow = df_telemetry["Discharge"].iloc[0]
    peak_flow = df_telemetry["Discharge"].max()
    is_critical = peak_flow > station['threshold']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Real-Time Flow", f"{current_flow:.1f} m³/s")
    m2.metric("7-Day Forecast Peak", f"{peak_flow:.1f} m³/s")
    m3.metric("Station Danger Level", f"{station['threshold']:.0f} m³/s")
    m4.metric("Risk Status", "🚨 CRITICAL" if is_critical else "🟢 NOMINAL")

st.divider()

# --- CHARTS & MAP ---
col1, col2 = st.columns([1.8, 1.2])

with col1:
    st.subheader("📊 Forecast vs. Historical 2022 Benchmark")
    if not df_telemetry.empty:
        # Forecast Area
        chart = alt.Chart(df_telemetry).mark_area(opacity=0.4, color='#38bdf8').encode(
            x=alt.X('Date_Label:O', title='Date'),
            y=alt.Y('Discharge:Q', title='Discharge (m³/s)'),
            tooltip=['Date_Label', 'Discharge']
        ).properties(height=250)

        # Danger Threshold
        thresh_line = alt.Chart(pd.DataFrame({'y': [station['threshold']]})).mark_rule(
            color='#ef4444', strokeDash=[4, 4]
        ).encode(y='y:Q')

        # 2022 Historical Benchmark Line
        hist_line = alt.Chart(pd.DataFrame({'y': [station['hist_peak']]})).mark_rule(
            color='#eab308', strokeDash=[2, 2]
        ).encode(y='y:Q')

        st.altair_chart(chart + thresh_line + hist_line, use_container_width=True)

    # 3D PyDeck Map
    map_df = pd.DataFrame([{"lat": station['lat'], "lon": station['lon']}])
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", map_df, get_position=["lon", "lat"], get_color=[239, 68, 68] if is_critical else [34, 197, 94], get_radius=3000)],
        initial_view_state=pdk.ViewState(latitude=station['lat'], longitude=station['lon'], zoom=10, pitch=45),
        map_style="mapbox://styles/mapbox/dark-v10"
    ), height=200)

with col2:
    st.subheader("🚨 AI Incident Dispatch & Reporting")
    
    class OperationalAdvisory(BaseModel):
        risk_level: str = Field(description="LOW, MODERATE, HIGH, or CRITICAL")
        advisory_bn: str = Field(description="Bengali response advisory")
        advisory_en: str = Field(description="English response advisory")
        protocols: list[str] = Field(description="Key action steps")

    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    advisory_text = "No active advisory."

    if api_key and not df_telemetry.empty:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Station: {selected_station}. Flow: {current_flow:.1f} m3/s, Peak: {peak_flow:.1f} m3/s, Threshold: {station['threshold']:.0f} m3/s. Provide advisory."
            
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json", "response_schema": OperationalAdvisory}
            )
            data = json.loads(res.text)
            
            st.warning(f"Threat Level: {data.get('risk_level')}")
            st.write(f"**বাংলা:** {data.get('advisory_bn')}")
            st.write(f"**English:** {data.get('advisory_en')}")
            
            advisory_text = f"Threat Level: {data.get('risk_level')}\nEN: {data.get('advisory_en')}\nBN: {data.get('advisory_bn')}"
            
        except Exception:
            st.error("AI service updating...")

    # --- REPORT DOWNLOAD BUTTON ---
    report_content = f"""OFFICIAL FLOOD SITUATION REPORT
Station: {selected_station}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Current Discharge: {current_flow:.1f} m3/s
Peak Forecast Discharge: {peak_flow:.1f} m3/s
Threshold Level: {station['threshold']:.0f} m3/s

AI DISPATCH SUMMARY:
{advisory_text}
"""
    st.download_button(
        label="📄 Export Operational Report (TXT)",
        data=report_content,
        file_name=f"Flood_Report_{selected_station.split()[0]}_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )
