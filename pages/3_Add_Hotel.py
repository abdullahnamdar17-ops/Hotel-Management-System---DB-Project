import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("🏩 Add New Hotel")
st.markdown("---")

with st.form("add_hotel_form"):
    col1, col2 = st.columns(2)
    with col1:
        hotel_name     = st.text_input("Hotel Name *")
        contact_phone  = st.text_input("Contact Phone *")
        street_address = st.text_input("Street Address *")
        city           = st.text_input("City *")
    with col2:
        state_province = st.text_input("State / Province *")
        zip_code       = st.text_input("ZIP Code *")
        star_rating    = st.select_slider("Star Rating", options=[1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0], value=3.0)

    submitted = st.form_submit_button("➕ Add Hotel")

if submitted:
    if not all([hotel_name, contact_phone, street_address, city, state_province, zip_code]):
        st.error("Please fill in all required fields.")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hotels
                    (hotel_name, contact_phone, street_address, city, state_province, zip_code, star_rating)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (hotel_name, contact_phone, street_address, city, state_province, zip_code, star_rating))
            conn.commit()
            st.success(f"✅ Hotel **{hotel_name}** added successfully!")
        except Exception as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close(); conn.close()

st.markdown("---")
st.subheader("🏨 Existing Hotels")
try:
    import pandas as pd
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM hotels ORDER BY hotel_id DESC", conn)
    conn.close()
    if df.empty:
        st.info("No hotels added yet.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)
except Exception as e:
    st.error(f"Error loading hotels: {e}")
