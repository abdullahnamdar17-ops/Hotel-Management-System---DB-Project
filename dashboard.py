from datetime import date

import pandas as pd
import streamlit as st

from db_connection import get_connection


def load_dashboard():
    """Load the operational summary without changing any database records."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM hotels) AS hotels,
                (SELECT COUNT(*) FROM guests) AS guests,
                (SELECT COUNT(*) FROM rooms) AS total_rooms,
                (SELECT COUNT(*) FROM rooms WHERE room_status = 'available') AS available_rooms,
                (SELECT COUNT(*) FROM rooms WHERE room_status = 'occupied') AS occupied_rooms,
                (SELECT COUNT(*) FROM bookings
                    WHERE booking_status IN ('reserved', 'checked_in')) AS active_bookings,
                (SELECT COALESCE(SUM(amount), 0) FROM payments
                    WHERE payment_status = 'paid') AS paid_revenue
            """
        )
        summary = cursor.fetchone()

        upcoming = pd.read_sql(
            """
            SELECT
                b.booking_id AS `Booking`,
                CONCAT(p.first_name, ' ', p.last_name) AS `Guest`,
                h.hotel_name AS `Hotel`,
                b.check_in_date AS `Check-in`,
                b.check_out_date AS `Check-out`,
                b.booking_status AS `Status`
            FROM bookings b
            JOIN guests g ON g.guest_id = b.guest_id
            JOIN persons p ON p.person_id = g.guest_id
            JOIN hotels h ON h.hotel_id = b.hotel_id
            WHERE b.check_out_date >= CURDATE()
              AND b.booking_status <> 'cancelled'
            ORDER BY b.check_in_date, b.booking_id
            LIMIT 8
            """,
            conn,
        )

        room_status = pd.read_sql(
            """
            SELECT room_status AS status, COUNT(*) AS rooms
            FROM rooms
            GROUP BY room_status
            ORDER BY rooms DESC
            """,
            conn,
        )

        booking_status = pd.read_sql(
            """
            SELECT booking_status AS status, COUNT(*) AS bookings
            FROM bookings
            GROUP BY booking_status
            ORDER BY bookings DESC
            """,
            conn,
        )

        revenue = pd.read_sql(
            """
            SELECT DATE_FORMAT(payment_date, '%Y-%m') AS month,
                   SUM(amount) AS revenue
            FROM payments
            WHERE payment_status = 'paid'
              AND payment_date >= DATE_SUB(CURDATE(), INTERVAL 5 MONTH)
            GROUP BY DATE_FORMAT(payment_date, '%Y-%m')
            ORDER BY month
            """,
            conn,
        )
        return summary, upcoming, room_status, booking_status, revenue, None
    except Exception as exc:
        empty = pd.DataFrame()
        return {}, empty, empty, empty, empty, str(exc)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


summary, upcoming, room_status, booking_status, revenue, load_error = load_dashboard()

st.markdown(
    f"""
    <section class="hero">
        <div class="hero-kicker">Property operations · {date.today():%d %B %Y}</div>
        <h1 class="hero-title">Good day. Here’s your hotel overview.</h1>
        <p class="hero-copy">
            Monitor reservations, room availability, guests and revenue from one focused workspace.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

if load_error:
    st.error(f"Dashboard data could not be loaded: {load_error}")

total_rooms = int(summary.get("total_rooms") or 0)
occupied_rooms = int(summary.get("occupied_rooms") or 0)
available_rooms = int(summary.get("available_rooms") or 0)
occupancy = (occupied_rooms / total_rooms * 100) if total_rooms else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="medium")
kpi1.metric(
    "Occupancy",
    f"{occupancy:.0f}%",
    f"{occupied_rooms} of {total_rooms} rooms",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
kpi2.metric(
    "Available rooms",
    f"{available_rooms:,}",
    f"{int(summary.get('hotels') or 0)} properties",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
kpi3.metric(
    "Active reservations",
    f"{int(summary.get('active_bookings') or 0):,}",
    f"{int(summary.get('guests') or 0):,} guests",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
kpi4.metric(
    "Paid revenue",
    f"${float(summary.get('paid_revenue') or 0):,.0f}",
    "Paid total",
    delta_color="off",
    delta_arrow="off",
    border=True,
)

st.markdown('<div class="section-heading">Today’s operations</div>', unsafe_allow_html=True)
left, right = st.columns([1.65, 1], gap="large")

with left:
    st.subheader("Upcoming stays")
    st.markdown(
        '<p class="panel-note">The next active arrivals and in-house reservations.</p>',
        unsafe_allow_html=True,
    )
    if upcoming.empty:
        st.info("No upcoming stays are recorded yet.")
    else:
        st.dataframe(
            upcoming,
            hide_index=True,
            width="stretch",
            column_config={
                "Booking": st.column_config.NumberColumn(format="#%d"),
                "Check-in": st.column_config.DateColumn(format="DD MMM"),
                "Check-out": st.column_config.DateColumn(format="DD MMM"),
            },
        )

with right:
    st.subheader("Room status")
    st.markdown(
        '<p class="panel-note">Current room inventory by operational state.</p>',
        unsafe_allow_html=True,
    )
    if room_status.empty:
        st.info("Add rooms to see the inventory breakdown.")
    else:
        st.bar_chart(
            room_status.set_index("status"),
            color="#B48A4A",
            horizontal=True,
            height=285,
        )

st.markdown('<div class="section-heading">Performance snapshot</div>', unsafe_allow_html=True)
chart_left, chart_right = st.columns(2, gap="large")

with chart_left:
    st.subheader("Reservations by status")
    st.markdown(
        '<p class="panel-note">A quick view of the reservation pipeline.</p>',
        unsafe_allow_html=True,
    )
    if booking_status.empty:
        st.info("Create a booking to populate this chart.")
    else:
        st.bar_chart(
            booking_status.set_index("status"),
            color="#243746",
            height=260,
        )

with chart_right:
    st.subheader("Paid revenue")
    st.markdown(
        '<p class="panel-note">Monthly paid transactions from the last six months.</p>',
        unsafe_allow_html=True,
    )
    if revenue.empty:
        st.info("Recorded paid transactions will appear here.")
    else:
        st.area_chart(
            revenue.set_index("month"),
            color="#B48A4A",
            height=260,
        )

st.markdown('<div class="section-heading">Quick actions</div>', unsafe_allow_html=True)
qa1, qa2, qa3, qa4 = st.columns(4, gap="medium")
with qa1:
    st.page_link("pages/1_Add_Guest.py", label="Add a guest", icon="👤", width="stretch")
with qa2:
    st.page_link("pages/6_Add_Booking.py", label="Create booking", icon="📅", width="stretch")
with qa3:
    st.page_link("pages/4_Add_Room.py", label="Add a room", icon="🛏️", width="stretch")
with qa4:
    st.page_link("pages/8_Payments.py", label="Record payment", icon="💳", width="stretch")

st.caption("Use the sidebar for complete hotel, guest, booking, payment and review management.")
