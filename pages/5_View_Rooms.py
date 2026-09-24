import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("🔍 View Rooms")
st.markdown("---")

try:
    conn = get_connection()
    hotels_df = pd.read_sql("SELECT hotel_id, hotel_name FROM hotels", conn)
    conn.close()
except Exception as e:
    st.error(f"Error: {e}"); st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    hotel_options = ["All"] + [f"{r['hotel_id']} – {r['hotel_name']}" for _, r in hotels_df.iterrows()]
    hotel_filter = st.selectbox("Filter by Hotel", hotel_options)
with col2:
    status_filter = st.selectbox("Filter by Status", ["All", "available", "occupied", "maintenance", "cleaning"])
with col3:
    type_filter = st.text_input("🔍 Search Room Type")

try:
    conn = get_connection()
    query = """
        SELECT r.room_id, h.hotel_name, r.room_number,
               rt.type_name, rt.capacity, rt.base_price, r.room_status
        FROM rooms r
        JOIN hotels h ON r.hotel_id = h.hotel_id
        JOIN room_types rt ON r.room_type_id = rt.room_type_id
        WHERE 1=1
    """
    params = []
    if hotel_filter != "All":
        hid = int(hotel_filter.split(" – ")[0])
        query += " AND r.hotel_id = %s"; params.append(hid)
    if status_filter != "All":
        query += " AND r.room_status = %s"; params.append(status_filter)
    if type_filter:
        query += " AND rt.type_name LIKE %s"; params.append(f"%{type_filter}%")
    query += " ORDER BY r.room_id DESC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    # Metrics
    total = len(df)
    avail = len(df[df["room_status"] == "available"]) if not df.empty else 0
    occup = len(df[df["room_status"] == "occupied"]) if not df.empty else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Rooms", total)
    m2.metric("Available", avail)
    m3.metric("Occupied", occup)

    if df.empty:
        st.info("No rooms match your filters.")
    else:
        df.columns = ["Room ID", "Hotel", "Room No.", "Type", "Capacity", "Base Price ($/night)", "Status"]
        st.dataframe(df, width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Database error: {e}")

st.markdown("---")
st.subheader("✏️ Update Room Status")
with st.form("update_room_status"):
    c1, c2 = st.columns(2)
    with c1: rid = st.number_input("Room ID", min_value=1, step=1)
    with c2: new_status = st.selectbox("New Status", ["available", "occupied", "maintenance", "cleaning"])
    if st.form_submit_button("Update Status"):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("UPDATE rooms SET room_status=%s WHERE room_id=%s", (new_status, rid))
            conn.commit()
            if cursor.rowcount:
                st.success(f"Room {rid} status updated to '{new_status}'.")
            else:
                st.warning("Room ID not found.")
            cursor.close(); conn.close()
        except Exception as e:
            st.error(f"Error: {e}")
