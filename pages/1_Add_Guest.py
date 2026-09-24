import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("👤 Add New Guest")
st.markdown("---")

with st.form("add_guest_form"):
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name *")
        email      = st.text_input("Email *")
        age        = st.number_input("Age *", min_value=18, max_value=120, value=25)
        city       = st.text_input("City *")
        zip_code   = st.text_input("ZIP Code *")
    with col2:
        last_name      = st.text_input("Last Name *")
        phone          = st.text_input("Phone *")
        street_address = st.text_input("Street Address *")
        state_province = st.text_input("State / Province *")

    col3, col4 = st.columns(2)
    with col3:
        guest_status = st.selectbox("Guest Status", ["active", "inactive", "banned"])
    with col4:
        loyalty_level = st.selectbox("Loyalty Level", ["none", "bronze", "silver", "gold", "platinum"])

    submitted = st.form_submit_button("➕ Add Guest")

if submitted:
    if not all([first_name, last_name, email, phone, street_address, city, state_province, zip_code]):
        st.error("Please fill in all required fields.")
    else:
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            cursor.execute("""
                INSERT INTO persons
                    (first_name, last_name, email, phone, age,
                     street_address, city, state_province, zip_code)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (first_name, last_name, email, phone, age,
                  street_address, city, state_province, zip_code))

            person_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO guests (guest_id, guest_status, loyalty_level)
                VALUES (%s,%s,%s)
            """, (person_id, guest_status, loyalty_level))

            conn.commit()
            st.success(f"✅ Guest **{first_name} {last_name}** added successfully!")
        except Exception as e:
            if conn is not None:
                conn.rollback()
            st.error(f"Database error: {e}")
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
