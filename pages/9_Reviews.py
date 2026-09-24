import streamlit as st
import datetime
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("⭐ Reviews")
st.markdown("---")

tab1, tab2 = st.tabs(["➕ Submit Review", "📊 View Reviews"])

with tab1:
    st.info("A review is linked to a completed booking. Only one review is allowed per booking.")
    with st.form("add_review_form"):
        col1, col2 = st.columns(2)
        with col1:
            booking_id  = st.number_input("Booking ID *", min_value=1, step=1)
            rating      = st.slider("Rating ⭐", min_value=1, max_value=5, value=5)
        with col2:
            review_date = st.date_input("Review Date *", value=datetime.date.today())
        review_text = st.text_area("Review Text (optional)", height=120)

        submitted = st.form_submit_button("⭐ Submit Review")

    if submitted:
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT booking_id FROM bookings WHERE booking_id=%s", (booking_id,))
            if not cursor.fetchone():
                st.error(f"Booking ID {booking_id} not found.")
            else:
                cursor.execute("""
                    INSERT INTO reviews (booking_id, rating, review_text, review_date)
                    VALUES (%s,%s,%s,%s)
                """, (booking_id, rating, review_text or None, review_date))
                conn.commit()
                st.success(f"✅ Review submitted for Booking #{booking_id}! Rating: {'⭐'*rating}")
            cursor.close(); conn.close()
        except Exception as e:
            if "Duplicate" in str(e):
                st.error("A review already exists for this booking.")
            else:
                st.error(f"Database error: {e}")

with tab2:
    col1, col2 = st.columns(2)
    with col1: min_rating = st.selectbox("Min Rating", [1,2,3,4,5], index=0)
    with col2: hotel_search = st.text_input("🔍 Search Hotel")

    try:
        conn = get_connection()
        query = """
            SELECT rv.review_id, rv.booking_id,
                   CONCAT(p.first_name,' ',p.last_name) AS guest,
                   h.hotel_name, rv.rating, rv.review_text, rv.review_date
            FROM reviews rv
            JOIN bookings b ON rv.booking_id = b.booking_id
            JOIN guests g ON b.guest_id = g.guest_id
            JOIN persons p ON p.person_id = g.guest_id
            JOIN hotels h ON b.hotel_id = h.hotel_id
            WHERE rv.rating >= %s
        """
        params = [min_rating]
        if hotel_search:
            query += " AND h.hotel_name LIKE %s"; params.append(f"%{hotel_search}%")
        query += " ORDER BY rv.review_id DESC"

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        if df.empty:
            st.info("No reviews found.")
        else:
            avg_rating = df["rating"].mean()
            m1, m2 = st.columns(2)
            m1.metric("Total Reviews", len(df))
            m2.metric("Average Rating", f"{avg_rating:.1f} ⭐")

            st.markdown("---")
            for _, row in df.iterrows():
                stars = "⭐" * int(row["rating"])
                text = row["review_text"] if row["review_text"] else "_No written review._"
                st.markdown(f"""
                <div class="review-card">
                    <div class="review-stars">{stars}</div>
                    <div class="review-guest">{row['guest']}</div>
                    <div class="review-hotel">🏨 {row['hotel_name']} &nbsp;|&nbsp; 📅 {row['review_date']} &nbsp;|&nbsp; Booking #{int(row['booking_id'])}</div>
                    <p style="margin-top:0.6rem;color:#333;">{text}</p>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Database error: {e}")
