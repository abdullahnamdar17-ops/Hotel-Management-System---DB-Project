import streamlit as st

from ui_styles import apply_styles


st.set_page_config(
    page_title="Hotel Management System",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()

pages = {
    "Overview": [
        st.Page(
            "dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:",
            default=True,
        ),
    ],
    "Front desk": [
        st.Page("pages/1_Add_Guest.py", title="Add guest", icon=":material/person_add:"),
        st.Page("pages/2_View_Guests.py", title="Guest directory", icon=":material/groups:"),
        st.Page("pages/6_Add_Booking.py", title="New booking", icon=":material/event_available:"),
        st.Page("pages/7_View_Bookings.py", title="Reservations", icon=":material/calendar_month:"),
    ],
    "Property": [
        st.Page("pages/3_Add_Hotel.py", title="Add hotel", icon=":material/domain_add:"),
        st.Page("pages/4_Add_Room.py", title="Add room", icon=":material/bedroom_parent:"),
        st.Page("pages/5_View_Rooms.py", title="Room inventory", icon=":material/meeting_room:"),
    ],
    "Finance & feedback": [
        st.Page("pages/8_Payments.py", title="Payments", icon=":material/payments:"),
        st.Page("pages/9_Reviews.py", title="Reviews", icon=":material/star:"),
    ],
}

selected_page = st.navigation(pages)
selected_page.run()
