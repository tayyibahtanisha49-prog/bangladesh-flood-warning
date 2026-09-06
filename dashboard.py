import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="Bangladesh Flood Early Warning System", page_icon="🌊", layout="wide")

class FloodAdvisory(BaseModel):
    station_name: str = Field(description="Name of the river gauge station")
    district: str = Field(description="District in Bangladesh")
    risk_level: str = Field(description="Low, Moderate, High, or Critical")
    time_to_impact_hours: int = Field(description="Hours before critical flooding")
    headline_bn: str = Field(description="Short emergency headline in Bengali")
    advisory_bn: str = Field(description="Clear, actionable instructions for residents in Bengali")
    advisory_en: str = Field(description="Clear, actionable instructions in English")

st.title("🌊 Bangladesh Flood Early Warning System")
st.caption("Powered by Open-Meteo Hydrological API & Gemini 3.6 Flash")

# Sidebar auto-refresh controls
st.sidebar.header("⚙️ Auto-Refresh Settings")
enable_auto = st.sidebar.toggle("Enable Live Auto-Refresh", value=False)
refresh_interval = st.sidebar.select_slider(
    "Refresh Interval (seconds):",
    options=[10, 30, 60, 120, 300],
    value=30,
    disabled=not enable_auto
)

run_every_val = refresh_interval if enable_auto else None

@st.fragment(run_every=run_every_val)
def render_dashboard():
    url = "https://flood-api.open-meteo.com/v1/flood"
    params = {
        "latitude": 25.0658,
        "longitude": 91.4071,
        "daily": "river_discharge",
        "forecast_days": 3
    }
    
    try:
        res = requests.get(url, params=params).json()
        dates = res["daily"]["time"]
        discharges = res["daily"]["river_discharge"]
    except Exception as e:
        st.error(f"Failed to fetch data from Open-Meteo API: {e}")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📊 Surma River Discharge Forecast (m³/s)")
        chart_data = {dates[i]: discharges[i] for i in range(len(dates))}
        st.line_chart(chart_data)

    with col2:
        st.subheader("📢 Live Emergency Dispatch")
        client = genai.Client(api_key=api_key)
        telemetry_summary = f"Station: Sunamganj (Surma River). Forecast m³/s: {dates[0]}: {discharges[0]}, {dates[1]}: {discharges[1]}, {dates[2]}: {discharges[2]}"
        
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=f"Analyze live data and issue an emergency warning:\n{telemetry_summary}",
                config=types.GenerateContentConfig(
                    system_instruction="You are a disaster response coordinator for Bangladesh.",
                    response_mime_type="application/json",
                    response_schema=FloodAdvisory
                )
            )
            
            alert = json.loads(response.text)
            
            if alert['risk_level'] in ['High', 'Critical']:
                st.error(f"🚨 **Risk Level:** {alert['risk_level']} | **Impact in:** ~{alert['time_to_impact_hours']} Hours")
            else:
                st.warning(f"⚠️ **Risk Level:** {alert['risk_level']} | **Impact in:** ~{alert['time_to_impact_hours']} Hours")

            st.markdown(f"### {alert['headline_bn']}")
            st.markdown(f"**🇧🇩 বাংলা নির্দেশিকা:**\n{alert['advisory_bn']}")
            st.markdown(f"**🇬🇧 English Advisory:**\n{alert['advisory_en']}")

        except APIError:
            st.error("⚠️ Gemini API is temporarily busy (503). Retrying on next interval...")

render_dashboard()
