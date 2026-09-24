import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("📋 View Bookings")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    status_filter = st.selectbox("Filter by Status", ["All", "reserved", "checked_in", "checked_out", "cancelled"])
with col2:
    search_guest = st.text_input("🔍 Search by Guest Name")

try:
    conn = get_connection()
    query = """
        SELECT b.booking_id, CONCAT(p.first_name,' ',p.last_name) AS guest,
               h.hotel_name, b.booking_date, b.check_in_date, b.check_out_date,
               b.booking_status,
               GROUP_CONCAT(r.room_number SEPARATOR ', ') AS rooms,
               SUM(DATEDIFF(b.check_out_date, b.check_in_date) * br.agreed_nightly_rate) AS total_cost
        FROM bookings b
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN persons p ON p.person_id = g.guest_id
        JOIN hotels h ON b.hotel_id = h.hotel_id
        LEFT JOIN booking_rooms br ON b.booking_id = br.booking_id
        LEFT JOIN rooms r ON br.room_id = r.room_id
        WHERE 1=1
    """
    params = []
    if status_filter != "All":
        query += " AND b.booking_status = %s"; params.append(status_filter)
    if search_guest:
        query += " AND (p.first_name LIKE %s OR p.last_name LIKE %s)"
        params += [f"%{search_guest}%", f"%{search_guest}%"]
    query += " GROUP BY b.booking_id ORDER BY b.booking_id DESC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Bookings", len(df))
        m2.metric("Reserved", len(df[df["booking_status"]=="reserved"]))
        m3.metric("Checked In", len(df[df["booking_status"]=="checked_in"]))
        m4.metric("Cancelled", len(df[df["booking_status"]=="cancelled"]))

    if df.empty:
        st.info("No bookings found.")
    else:
        df.columns = ["Booking ID","Guest","Hotel","Booking Date","Check-in","Check-out","Status","Rooms","Total Cost ($)"]
        st.dataframe(df, width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Database error: {e}")

st.markdown("---")
st.subheader("✏️ Update Booking Status")
with st.form("update_booking_status"):
    c1, c2 = st.columns(2)
    with c1: bid = st.number_input("Booking ID", min_value=1, step=1)
    with c2: new_status = st.selectbox("New Status", ["reserved","checked_in","checked_out","cancelled"])
    if st.form_submit_button("Update Status"):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("UPDATE bookings SET booking_status=%s WHERE booking_id=%s", (new_status, bid))
            conn.commit()
            if cursor.rowcount:
                st.success(f"Booking #{bid} status updated to '{new_status}'.")
            else:
                st.warning("Booking ID not found.")
            cursor.close(); conn.close()
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
st.subheader("🛏️ Assign Room to Booking")
with st.form("assign_room_form"):
    c1, c2, c3 = st.columns(3)
    with c1: assign_bid  = st.number_input("Booking ID", min_value=1, step=1, key="abid")
    with c2: assign_rid  = st.number_input("Room ID", min_value=1, step=1)
    with c3: assign_rate = st.number_input("Nightly Rate ($)", min_value=0.01, value=100.0, format="%.2f")
    if st.form_submit_button("Assign Room"):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("INSERT INTO booking_rooms (booking_id,room_id,agreed_nightly_rate) VALUES (%s,%s,%s)",
                           (assign_bid, assign_rid, assign_rate))
            conn.commit()
            st.success(f"Room {assign_rid} assigned to Booking #{assign_bid}.")
            cursor.close(); conn.close()
        except Exception as e:
            st.error(f"Error: {e}")
