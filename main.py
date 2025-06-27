import streamlit as st
from pymavlink import mavutil
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
            latitude, longtitude = mpInfo.lat, mpInfo.lon
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
                <b>Battery: </b> Figure out how to display this</br>
                <b>Speed (X, Y): </b> {speed_x}, {speed_y}</br>
                <b>GPS Coordinates: </b> ({latitude}, {longtitude})</br>
                </div>
            </div>
            """, unsafe_allow_html=True)
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
