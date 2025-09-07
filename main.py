import streamlit as st
from pymavlink import mavutil
import folium
from streamlit_folium import st_folium
import time
import requests

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

# FOR THE LLM + SLM
if query:
    st.subheader("LLM: ")
    # for fast api & flask api slm:
    response = requests.post("http://127.0.0.1:8000/get_waypoints/", json={"user_prompt": query})

    # for fast api & flask api & bottle api (while testing slm with apache jmeter):
    # response = requests.post("http://127.0.0.1:14550/get_waypoints/", json={"user_prompt": query})

    # for bottle api slm:
    # response = requests.post("http://127.0.0.1:7860/get_waypoints/", json={"user_prompt": query})

    # for fast api & flask api & bottle api llm:
    # responseQuery = requests.post("http://127.0.0.1:8000/get_waypoints/", json={"user_prompt": query})

    if response.ok:
        st.write("**Waypoints:**", response.json()["waypoints"])
    else:
        st.error("❌ Could not get waypoints")

st.divider()

# FOR THE YOLO + SMOLVLM MODELS:
st.header("Obstacles Dashboard")
obstacleCollector = st.button("Collect Obstacles")
#
# if obstacleCollector:
#     # for fast api & flask api & bottle api (YOLO)
#     responseObstacle = requests.post("http://127.0.0.1:8000/get_obstacles/")
#
#
#     if responseObstacle.ok:
#         data = responseObstacle.json()
#         st.write("**Obstacles:**", data["obstacles"])
#         st.write("**Description:**", data["description"])
#
#     else:
#         st.error("❌ Could not get obstacles")

if obstacleCollector:
    with st.spinner("Collecting obstacles"):
        max_attempts = 5
        attempt = 0
        success = False

        while attempt < max_attempts:
            try:
                response = requests.post("http://127.0.0.1:8000/get_obstacles/")
                # response = requests.post("http://127.0.0.1:8000/get_obstacles/")
                if response.ok:
                    data = response.json()
                    if data.get("description") and data["description"]:
                        st.write("**Description:**", data["description"])
                        success = True
                        break
            except Exception as e:
                st.warning(f"Attempt {attempt + 1}: {e}")

            attempt += 1
            time.sleep(5)

        if not success:
            st.error("❌ Could not get obstacles")

st.divider()


# CONNECTING TO MISSION PLANNER
if startButton and not st.session_state.connected:
    try:
        # mpConnection = mavutil.mavlink_connection('COM14', baud=57600)
        mpConnection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
        mpConnection.wait_heartbeat(timeout=10)
        st.session_state.connection = mpConnection
        st.session_state.connected = True
    except Exception as e:
        st.error("Failed to connect: " + str(e))

if stopButton and st.session_state.connected:
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
        mpInfo = st.session_state.connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=5)
        print(mpInfo)
        # waits for a msg from mavlink with all the info^^^
        if mpInfo:
            speed_x, speed_y = mpInfo.vx, mpInfo.vy
            latitude, longitude = mpInfo.lat / 1E7, mpInfo.lon / 1E7
            battery = st.session_state.connection.recv_match(type='BATTERY_STATUS', blocking=True, timeout=2)
            print(mpInfo)
            if battery:
                voltage = (battery.voltages[0]) / 1000
                batteryDisplay = f"{voltage: .2f} V"
            else:
                batteryDisplay = "Not Available"
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
                <b>Battery: </b> {batteryDisplay} </br>
                <b>Speed (X, Y): </b> {speed_x}, {speed_y}</br>
                <b>GPS Coordinates: </b> ({latitude}, {longitude})</br>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()

            # OSM map display
            time.sleep(15)
            map = folium.Map(location=[mpInfo.lat / 1E7, mpInfo.lon / 1E7],
                             tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"
                                   "/{z}/{y}/{x}",
                             attr="Esri", zoom_start=18)
            folium.Marker([mpInfo.lat / 1E7, mpInfo.lon / 1E7], tooltip="BADGER's Location").add_to(map)
            st_folium(map, width=700)

    except Exception as e:
        st.error("Unable to Retrieve Data: " + str(e))

# SENDING WAYPOINTS TO MISSION PLANNER/MAVPROXY
waypointsButton = st.sidebar.button("Send Waypoints")

if st.session_state.connected and "waypoints" in st.session_state:
    if waypointsButton:
        try:
            waypoints = st.session_state["waypoints"]
            mp = st.session_state.connection
            # https://discuss.ardupilot.org/t/clear-all-mission-mavlink-message-not-working/93252
            # https://discuss.bluerobotics.com/t/sending-mavproxy-messages-from-a-python-program/1515/2
            mp.mav.mission_clear_all_send(mp.target_system, mp.target_component)
            mp.mav.mission_set_current_send(mp.target_system, mp.target_component, 0)
            mp.mav.mission_count_send(mp.target_system, mp.target_component, len(waypoints))

            altitude = 0
            for i, wp in enumerate(waypoints):
                mp.mav.mission_item_send(
                    mp.target_system,
                    mp.target_component,
                    i,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    0, 1,
                    0, 0, 0, 0,
                    wp["lat"], wp["lon"],
                    altitude
                )
            st.success("✅ Sent waypoints to Mission Planner")
            time.sleep(2)

        except Exception as e:
            st.error(f"❌ Couldn't send waypoints to Mission Planner: {e}")

if st.session_state.connected:
    st.success("✅ Connected to Mission Planner")
else:
    st.warning("⚠️ Not connected to Mission Planner; Click 'Start Badger' to connect.")

# # placeholder values for demo of how it displays the values
# st.markdown(f"""
# <div style=""
#     display: flex;
#     justify-content: center;
#     align-items:center;
#     height: 100vh;
#     width: 100%;
#     margin: 0;
# ">
# <div style="
#     background-color: #363638;
#     padding: 25px;
#     border-radius: 10px;
#     box-shadow: 0 0 15px #ffffff;
#     margin-top: 20px;
#     color: white;
#     font-size: 18px;
#     width: 100%;
#     text-align: center;
# ">
#     <b style="font-size: 36px"> Badger Status </b></br>
#     Battery: Figure out how to display this</br>
#     Speed (X, Y): 2, 4</br>
#     GPS Coordinates: (x, y)</br>
# </div>
# </div>
# """, unsafe_allow_html=True)
#
# st.divider()
#
# map = folium.Map(location=[40,29], tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery"
#                                            "/MapServer/tile/{z}/{y}/{x}", attr="Esri", zoom_start=6)
# folium.Marker([40,29], tooltip="BADGER's Location").add_to(map)
# st_folium(map, width=700)
