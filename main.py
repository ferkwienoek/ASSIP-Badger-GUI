import streamlit as st
from pymavlink import mavutil
import folium
from streamlit_folium import st_folium
import time
import os

# Run with "streamlit run main.py"

# MAIN STREAMLIT LAYOUT
st.set_page_config(page_title="ASSIP BADGER")

st.markdown("""
<style>.glowing-text {
    text-shadow: 0 0 30px #90EE90, 0 0 70px #00FFFF, 0 0 90px #FFF
}
</style>
""", unsafe_allow_html=True)
st.markdown("<h1 class='glowing-text' style='text-align: center; color: white; font-size: 55px'>ASSIP 2025 - "
            "BADGER</h1>", unsafe_allow_html=True)
st.divider()

# To import images: st.image(os.path.join(os.getcwd()), "static", "image.whatever")
st.sidebar.title("Mission Control")

if "connected" not in st.session_state:
    st.session_state.connected = False
    st.session_state.connection = None

startButton = st.sidebar.button("Start Badger")
stopButton = st.sidebar.button("Stop Badger")

st.header("LLM Dashboard")

st.markdown("""
<style>.glowing-input {
    border: 2px solid #2e2e2e
}
</style>
""", unsafe_allow_html=True)

query = st.text_input(label="placeholder", label_visibility="collapsed", placeholder="Instruct the LLM")
# st.markdown('<div class="glowing-input">', unsafe_allow_html=True)

if query:
    # connect to the LLM once Shauryan informs what LLM is being used
    st.subheader("LLM: ")

st.divider()

# CONNECTING TO MISSION PLANNER
if startButton and not st.session_state.connected:
    try:
        mpConnection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
        mpConnection.wait_heartbeat()
        st.session_state.connection = mpConnection
        st.session_state.connected = True
        st.success("Connected to Mission Planner")
    except Exception as e:
        st.error("Failed to connect: " + str(e))

if stopButton and st.session_state.connected == False:
    try:
        st.session_state.connection.close()
    except:
        pass
    st.session_state.connected = False
    st.session_state.connection = None
    st.error("Disconnected from Mission Planner")

# streaming the telemetry
altDisplay = st.empty()
if st.session_state.connected:
    try:
        mpInfo = st.session_state.connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        # waits for a msg from mavlink with all the info^^^
        if mpInfo:
            speed_x, speed_y = mpInfo.vx, mpInfo.vy
            latitude, longitude = mpInfo.lat, mpInfo.lon
            battery = st.session_state.connection.recv_match(type='BATTERY_STATUS', blocking=True, timeout=2)
            if battery:
                voltage = (battery.voltages[0])/1000
                batteryDisplay = f"{voltage: .2f} V"
            st.markdown(f"""
            <div style=""
                display: flex;
                justify-content: center;
                align-items:center;
                height: 100vh;
                width: 100%;
                margin: 0;
            ">
                <div style="
                    background-color: #363638;
                    padding: 25px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px #279c46, 0 0 40px #1cb0b8;
                    margin-top: 20px;
                    color: white;
                    font-size: 18px;
                    width: 100%;
                    text-align: center;
                ">
                <b style="font-size: 36px"> Badger Status </b></br>
                <b>Battery: </b> batteryDisplay </br>
                <b>Speed (X, Y): </b> {speed_x}, {speed_y}</br>
                <b>GPS Coordinates: </b> ({latitude}, {longitude})</br>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()

            # OSM map display
            map = folium.Map(location=[40, 29],
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri", zoom_start=18)
            folium.Marker([40, 29], tooltip="BADGER's Location").add_to(map)
            st_folium(map, width=700)

    except Exception as e:
        st.error("Unable to Retrieve Data: " + str(e))


if st.session_state.connected:
    st.success("✅ Connected to Mission Planner")
else:
    st.warning("⚠️ Not connected to Mission Planner; Click 'Start Badger' to connect.")

# placeholder values for demo of how it displays the values
st.markdown(f"""
<div style=""
    display: flex;
    justify-content: center;
    align-items:center;
    height: 100vh;
    width: 100%;
    margin: 0;
">
<div style="
    background-color: #363638;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 0 15px #ffffff;
    margin-top: 20px;
    color: white;
    font-size: 18px;
    width: 100%;
    text-align: center;
">
    <b style="font-size: 36px"> Badger Status </b></br>
    Battery: Figure out how to display this</br>
    Speed (X, Y): 2, 4</br>
    GPS Coordinates: (x, y)</br>
</div>
</div>
""", unsafe_allow_html=True)

st.divider()

map = folium.Map(location=[40,29], tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery"
                                           "/MapServer/tile/{z}/{y}/{x}", attr="Esri", zoom_start=6)
folium.Marker([40,29], tooltip="BADGER's Location").add_to(map)
st_folium(map, width=700)
