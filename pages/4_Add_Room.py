import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("🛏️ Add New Room")
st.markdown("---")

def fetch_hotels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hotel_id, hotel_name FROM hotels ORDER BY hotel_name")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def fetch_room_types():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT room_type_id, type_name, base_price FROM room_types ORDER BY type_name")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

try:
    hotels     = fetch_hotels()
    room_types = fetch_room_types()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# Add Room Type section
st.subheader("📂 Manage Room Types")
with st.expander("➕ Add a New Room Type"):
    with st.form("add_room_type_form"):
        c1, c2, c3 = st.columns(3)
        with c1: rt_name     = st.text_input("Type Name (e.g. Suite) *")
        with c2: rt_capacity = st.number_input("Capacity *", min_value=1, value=2)
        with c3: rt_price    = st.number_input("Base Price ($/night) *", min_value=0.01, value=100.0, format="%.2f")
        rt_submitted = st.form_submit_button("Add Room Type")
    if rt_submitted:
        if not rt_name:
            st.error("Room type name is required.")
        else:
            try:
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("INSERT INTO room_types (type_name, capacity, base_price) VALUES (%s,%s,%s)",
                               (rt_name, rt_capacity, rt_price))
                conn.commit(); cursor.close(); conn.close()
                st.success(f"Room type '{rt_name}' added!"); st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")
st.subheader("🛏️ Add Room to a Hotel")

if not hotels:
    st.warning("Please add a hotel first (page 3).")
    st.stop()
if not room_types:
    st.warning("Please add at least one room type above first.")
    st.stop()

hotel_map     = {f"{h[0]} – {h[1]}": h[0] for h in hotels}
room_type_map = {f"{r[1]} (${r[2]}/night)": r[0] for r in room_types}

with st.form("add_room_form"):
    col1, col2 = st.columns(2)
    with col1:
        hotel_choice    = st.selectbox("Hotel *", list(hotel_map.keys()))
        room_number     = st.text_input("Room Number *", placeholder="e.g. 101")
    with col2:
        rt_choice       = st.selectbox("Room Type *", list(room_type_map.keys()))
        room_status     = st.selectbox("Room Status", ["available", "occupied", "maintenance", "cleaning"])

    submitted = st.form_submit_button("➕ Add Room")

if submitted:
    if not room_number:
        st.error("Room number is required.")
    else:
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rooms (hotel_id, room_type_id, room_number, room_status)
                VALUES (%s,%s,%s,%s)
            """, (hotel_map[hotel_choice], room_type_map[rt_choice], room_number, room_status))
            conn.commit()
            st.success(f"✅ Room **{room_number}** added successfully!")
        except Exception as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close(); conn.close()
