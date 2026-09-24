import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

st.title("👥 View Guests")
st.markdown("---")

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    search_name = st.text_input("🔍 Search by Name")
with col2:
    filter_status = st.selectbox("Filter by Status", ["All", "active", "inactive", "banned"])
with col3:
    filter_loyalty = st.selectbox("Filter by Loyalty", ["All", "none", "bronze", "silver", "gold", "platinum"])

try:
    conn = get_connection()
    query = """
        SELECT g.guest_id, p.first_name, p.last_name, p.email, p.phone, p.age,
               p.city, p.state_province, g.guest_status, g.loyalty_level
        FROM guests g
        JOIN persons p ON p.person_id = g.guest_id
        WHERE 1=1
    """
    params = []
    if search_name:
        query += " AND (p.first_name LIKE %s OR p.last_name LIKE %s)"
        params += [f"%{search_name}%", f"%{search_name}%"]
    if filter_status != "All":
        query += " AND g.guest_status = %s"
        params.append(filter_status)
    if filter_loyalty != "All":
        query += " AND g.loyalty_level = %s"
        params.append(filter_loyalty)
    query += " ORDER BY g.guest_id DESC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    st.markdown(f"**{len(df)} guest(s) found**")

    if df.empty:
        st.info("No guests match your filters.")
    else:
        df.columns = ["ID", "First Name", "Last Name", "Email", "Phone", "Age",
                      "City", "State/Province", "Status", "Loyalty"]
        st.dataframe(df, width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Database error: {e}")

st.markdown("---")
# Edit / Delete section
st.subheader("✏️ Edit or Delete a Guest")

guest_id_input = st.number_input("Enter Guest ID to edit/delete", min_value=1, step=1)
action = st.radio("Action", ["Edit", "Delete"], horizontal=True)

if action == "Delete":
    if st.button("🗑️ Delete Guest"):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM persons
                WHERE person_id = %s
                  AND EXISTS (
                      SELECT 1 FROM guests WHERE guest_id = %s
                  )
            """, (guest_id_input, guest_id_input))
            conn.commit()
            if cursor.rowcount:
                st.success(f"Guest ID {guest_id_input} deleted.")
            else:
                st.warning("No guest found with that ID.")
        except Exception as e:
            if conn is not None:
                conn.rollback()
            st.error(f"Error: {e}")
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

elif action == "Edit":
    if st.button("🔎 Load Guest"):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT g.guest_id, p.first_name, p.last_name, p.email, p.phone,
                       p.age, p.street_address, p.city, p.state_province,
                       p.zip_code, g.guest_status, g.loyalty_level
                FROM guests g
                JOIN persons p ON p.person_id = g.guest_id
                WHERE g.guest_id = %s
            """, (guest_id_input,))
            row = cursor.fetchone()
            if row:
                st.session_state["edit_guest"] = row
            else:
                st.warning("No guest found with that ID.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    if "edit_guest" in st.session_state:
        g = st.session_state["edit_guest"]
        with st.form("edit_guest_form"):
            c1, c2 = st.columns(2)
            with c1:
                fn   = st.text_input("First Name", value=g["first_name"])
                em   = st.text_input("Email", value=g["email"])
                ag   = st.number_input("Age", min_value=18, value=int(g["age"]))
                ct   = st.text_input("City", value=g["city"])
                zp   = st.text_input("ZIP Code", value=g["zip_code"])
            with c2:
                ln   = st.text_input("Last Name", value=g["last_name"])
                ph   = st.text_input("Phone", value=g["phone"])
                sa   = st.text_input("Street Address", value=g["street_address"])
                sp   = st.text_input("State/Province", value=g["state_province"])
            statuses = ["active","inactive","banned"]
            loyalties = ["none","bronze","silver","gold","platinum"]
            gs = st.selectbox("Status", statuses, index=statuses.index(g["guest_status"]))
            ll = st.selectbox("Loyalty", loyalties, index=loyalties.index(g["loyalty_level"]))
            save = st.form_submit_button("💾 Save Changes")
        if save:
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                conn.start_transaction()
                cursor.execute("""
                    UPDATE persons
                    SET first_name=%s,last_name=%s,email=%s,phone=%s,
                        age=%s,street_address=%s,city=%s,state_province=%s,zip_code=%s
                    WHERE person_id=%s
                """, (fn,ln,em,ph,ag,sa,ct,sp,zp,g["guest_id"]))
                cursor.execute("""
                    UPDATE guests
                    SET guest_status=%s,loyalty_level=%s
                    WHERE guest_id=%s
                """, (gs,ll,g["guest_id"]))
                conn.commit()
                st.success("Guest updated successfully!")
                del st.session_state["edit_guest"]
            except Exception as e:
                if conn is not None:
                    conn.rollback()
                st.error(f"Error: {e}")
            finally:
                if cursor is not None:
                    cursor.close()
                if conn is not None:
                    conn.close()
