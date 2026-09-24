import streamlit as st
import datetime
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("💳 Payments")
st.markdown("---")

tab1, tab2 = st.tabs(["➕ Add Payment", "📊 View Payments"])

with tab1:
    with st.form("add_payment_form"):
        col1, col2 = st.columns(2)
        with col1:
            booking_id     = st.number_input("Booking ID *", min_value=1, step=1)
            amount         = st.number_input("Amount ($) *", min_value=0.01, value=100.0, format="%.2f")
            payment_method = st.selectbox("Payment Method", ["cash","credit_card","debit_card","bank_transfer","online"])
        with col2:
            payment_date   = st.date_input("Payment Date *", value=datetime.date.today())
            payment_status = st.selectbox("Payment Status", ["paid","pending","refunded","failed"])

        submitted = st.form_submit_button("💳 Record Payment")

    if submitted:
        try:
            conn = get_connection(); cursor = conn.cursor()
            # verify booking exists
            cursor.execute("SELECT booking_id FROM bookings WHERE booking_id=%s", (booking_id,))
            if not cursor.fetchone():
                st.error(f"Booking ID {booking_id} does not exist.")
            else:
                cursor.execute("""
                    INSERT INTO payments (booking_id, payment_date, amount, payment_method, payment_status)
                    VALUES (%s,%s,%s,%s,%s)
                """, (booking_id, payment_date, amount, payment_method, payment_status))
                conn.commit()
                st.success(f"✅ Payment of **${amount:.2f}** recorded for Booking #{booking_id}!")
            cursor.close(); conn.close()
        except Exception as e:
            st.error(f"Database error: {e}")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        bid_filter    = st.number_input("Filter by Booking ID (0 = all)", min_value=0, step=1, key="pf_bid")
    with col2:
        pstatus_filter = st.selectbox("Filter by Status", ["All","paid","pending","refunded","failed"])

    try:
        conn = get_connection()
        query = """
            SELECT p.payment_id, p.booking_id,
                   CONCAT(pr.first_name,' ',pr.last_name) AS guest,
                   p.payment_date, p.amount, p.payment_method, p.payment_status
            FROM payments p
            JOIN bookings b ON p.booking_id = b.booking_id
            JOIN guests g ON b.guest_id = g.guest_id
            JOIN persons pr ON pr.person_id = g.guest_id
            WHERE 1=1
        """
        params = []
        if bid_filter > 0:
            query += " AND p.booking_id = %s"; params.append(bid_filter)
        if pstatus_filter != "All":
            query += " AND p.payment_status = %s"; params.append(pstatus_filter)
        query += " ORDER BY p.payment_id DESC"

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        if not df.empty:
            total_paid = df[df["payment_status"]=="paid"]["amount"].sum()
            m1, m2 = st.columns(2)
            m1.metric("Total Records", len(df))
            m2.metric("Total Paid ($)", f"{total_paid:,.2f}")

        if df.empty:
            st.info("No payments found.")
        else:
            df.columns = ["Payment ID","Booking ID","Guest","Date","Amount ($)","Method","Status"]
            st.dataframe(df, width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Database error: {e}")
