import streamlit as st
import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("📅 Add New Booking")
st.markdown("---")

try:
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT g.guest_id, p.first_name, p.last_name
        FROM guests g
        JOIN persons p ON p.person_id = g.guest_id
        ORDER BY p.last_name, p.first_name
    """)
    guests = cursor.fetchall()
    cursor.execute("SELECT hotel_id, hotel_name FROM hotels ORDER BY hotel_name")
    hotels = cursor.fetchall()
    cursor.close(); conn.close()
except Exception as e:
    st.error(f"Failed to load data: {e}"); st.stop()

if not guests:
    st.warning("No guests found. Add a guest first (page 1)."); st.stop()
if not hotels:
    st.warning("No hotels found. Add a hotel first (page 3)."); st.stop()

guest_map = {f"{g[0]} – {g[1]} {g[2]}": g[0] for g in guests}
hotel_map = {f"{h[0]} – {h[1]}": h[0] for h in hotels}

with st.form("add_booking_form"):
    col1, col2 = st.columns(2)
    with col1:
        guest_choice  = st.selectbox("Guest *", list(guest_map.keys()))
        check_in      = st.date_input("Check-in Date *", value=datetime.date.today() + datetime.timedelta(days=1))
        booking_date  = st.date_input("Booking Date *", value=datetime.date.today())
    with col2:
        hotel_choice  = st.selectbox("Hotel *", list(hotel_map.keys()))
        check_out     = st.date_input("Check-out Date *", value=datetime.date.today() + datetime.timedelta(days=3))
        booking_status = st.selectbox("Status", ["reserved", "checked_in", "checked_out", "cancelled"])

    st.markdown("**Select Rooms & Rates**")
    # Load available rooms for selected hotel dynamically (show all for simplicity)
    st.caption("After submitting the booking, rooms will be assigned automatically based on availability. Or you can pick a room ID manually.")

    room_id_input   = st.number_input("Room ID to assign (optional – enter 0 to skip)", min_value=0, step=1)
    nightly_rate    = st.number_input("Agreed Nightly Rate ($)", min_value=0.01, value=100.0, format="%.2f")

    submitted = st.form_submit_button("➕ Create Booking")

if submitted:
    hotel_id = hotel_map[hotel_choice]
    guest_id = guest_map[guest_choice]

    if check_out <= check_in:
        st.error("Check-out date must be after check-in date.")
    elif booking_date > check_in:
        st.error("Booking date must be on or before check-in date.")
    else:
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookings (guest_id, hotel_id, booking_date, check_in_date, check_out_date, booking_status)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (guest_id, hotel_id, booking_date, check_in, check_out, booking_status))
            conn.commit()
            booking_id = cursor.lastrowid

            if room_id_input > 0:
                cursor.execute("""
                    INSERT INTO booking_rooms (booking_id, room_id, agreed_nightly_rate)
                    VALUES (%s,%s,%s)
                """, (booking_id, room_id_input, nightly_rate))
                conn.commit()
                st.success(f"✅ Booking #{booking_id} created and Room {room_id_input} assigned!")
            else:
                st.success(f"✅ Booking #{booking_id} created! Assign a room from View Bookings.")

            cursor.close(); conn.close()
        except Exception as e:
            st.error(f"Database error: {e}")
