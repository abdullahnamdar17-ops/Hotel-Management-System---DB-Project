# 🏨 Hotel Management System

A full-stack hotel management web application built with **Streamlit** and **MySQL**. The operations dashboard surfaces occupancy, room availability, active reservations, upcoming stays, payment revenue, and status breakdowns from the live database.

---

## 📁 Project Structure

```
Hotel_Management_System/
│
├── app.py                        # Main home dashboard
├── dashboard.py                  # Live operations overview
├── ui_styles.py                  # Shared interface styling
├── db_connection.py              # MySQL connection helper
├── hotel_management_system.sql   # Database schema (run this first)
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── .streamlit/
│   └── config.toml               # Public visual theme
│
└── pages/
    ├── 1_Add_Guest.py
    ├── 2_View_Guests.py
    ├── 3_Add_Hotel.py
    ├── 4_Add_Room.py
    ├── 5_View_Rooms.py
    ├── 6_Add_Booking.py
    ├── 7_View_Bookings.py
    ├── 8_Payments.py
    └── 9_Reviews.py
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- MySQL Server running locally
- pip

---

### 2. Set Up the Database

1. Open **MySQL Workbench** or your MySQL client.
2. Open and run `hotel_management_system.sql`.
3. This will create the database and all tables automatically.

> **Warning:** The schema script resets existing project tables. Do not rerun it against a database containing data you want to keep.

---

### 3. Configure the Database Connection

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, then add your local credentials:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
[mysql]
host = "localhost"
user = "root"
password = "YOUR_MYSQL_PASSWORD"
database = "hotel_management_system"
```

The secrets file is excluded by `.gitignore` and must never be committed.

---

### 4. Install Python Dependencies

Open a terminal inside the `Hotel_Management_System` folder and run:

```bash
pip install -r requirements.txt
```

---

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## 🗺️ Pages Overview

| Page | Description |
|------|-------------|
| 🏠 Dashboard | Live KPIs, upcoming stays, room status, bookings, and revenue |
| 👤 Add Guest | Register a new guest |
| 👥 View Guests | Search, filter, edit, or delete guests |
| 🏩 Add Hotel | Add a new hotel property |
| 🛏️ Add Room | Add room types and rooms to hotels |
| 🔍 View Rooms | View & filter rooms; update room status |
| 📅 Add Booking | Create a new guest booking |
| 📋 View Bookings | View, filter, update bookings; assign rooms |
| 💳 Payments | Record and view payments per booking |
| ⭐ Reviews | Submit and view guest reviews |

---

## 🗄️ Database Tables

| Table | Purpose |
|-------|---------|
| `hotels` | Hotel properties |
| `persons` | Shared identity and contact details for guests and staff |
| `guests` | Guest status and loyalty profile linked to `persons` |
| `staff_roles` | Staff role definitions |
| `staff` | Hotel staff members |
| `room_types` | Room categories with base price |
| `rooms` | Individual hotel rooms |
| `bookings` | Guest reservations |
| `booking_rooms` | Many-to-many: bookings ↔ rooms |
| `payments` | Payment records per booking |
| `reviews` | One review per booking |

---

## 💡 Recommended Workflow

1. **Add a Hotel** (Page 3)
2. **Add Room Types** via the expander on Page 4
3. **Add Rooms** to the hotel (Page 4)
4. **Add Guests** (Page 1)
5. **Create a Booking** (Page 6) — link guest + hotel + room
6. **Record Payment** (Page 8)
7. **Submit Review** after checkout (Page 9)

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit,HTML,CSS
- **Interface**: Grouped navigation, responsive KPI cards, native charts, and shared theming
- **Backend**: Python 3
- **Database**: MySQL
- **Driver**: mysql-connector-python
- **Data**: pandas

---

## 📝 Notes

- Guest age must be ≥ 18 (enforced by DB constraint).
- Guest identity/contact data is stored in `persons`; guest-specific data is stored in `guests`.
- Check-out date must be after check-in date.
- Each booking can only have one review.
- Room numbers are unique per hotel.
