"""Hotel management web application, exported as a WSGI app for Vercel."""

from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
import os
import re
import secrets
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
import mysql.connector
from werkzeug.exceptions import HTTPException

from database import close_db, execute, query, transaction
from db_connection import ConfigurationError
from validation import ValidationError, choice, day, integer, money, text


GUEST_STATUS = ("active", "inactive", "banned")
LOYALTY = ("none", "bronze", "silver", "gold", "platinum")
ROOM_STATUS = ("available", "occupied", "maintenance", "cleaning")
BOOKING_STATUS = ("reserved", "checked_in", "checked_out", "cancelled")
ACTIVE_BOOKINGS = ("reserved", "checked_in")
PAYMENT_STATUS = ("paid", "pending", "refunded", "failed")
PAYMENT_METHOD = ("cash", "credit_card", "debit_card", "bank_transfer", "online")
NAVIGATION = (
    ("home", "Overview", "◇"), ("guests_new", "Add guest", "+"),
    ("guests", "Guests", "◉"), ("hotels", "Hotels", "▥"),
    ("rooms_new", "Add room", "+"), ("rooms", "Rooms", "▦"),
    ("bookings_new", "New booking", "+"), ("bookings", "Bookings", "▤"),
    ("payments", "Payments", "$"), ("reviews", "Reviews", "☆"),
)


def positive_filter(name):
    try:
        value = int(request.args.get(name, ""))
        return value if 1 <= value <= 2147483647 else None
    except ValueError:
        return None


def create_app(test_config=None):
    app = Flask(__name__, static_folder="public", static_url_path="")
    deployed = os.environ.get("VERCEL") == "1"
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        DEPLOYED=deployed,
        DEPLOYMENT_SECRET_CONFIGURED=bool(os.environ.get("SECRET_KEY")),
        APP_TIMEZONE=os.environ.get("APP_TIMEZONE", "Asia/Karachi"),
        SESSION_COOKIE_SECURE=deployed,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=65536,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    @app.context_processor
    def template_context():
        today = datetime.now(ZoneInfo(app.config["APP_TIMEZONE"])).date()
        return dict(
            navigation=NAVIGATION, csrf_token=csrf_token,
            guest_statuses=GUEST_STATUS, loyalty_levels=LOYALTY,
            room_statuses=ROOM_STATUS, booking_statuses=BOOKING_STATUS,
            payment_statuses=PAYMENT_STATUS, payment_methods=PAYMENT_METHOD,
            today=today, default_check_in=today+timedelta(days=1), default_check_out=today+timedelta(days=3),
            authenticated=not app.config["ADMIN_PASSWORD"] or session.get("authenticated", False),
            login_enabled=bool(app.config["ADMIN_PASSWORD"]),
        )

    @app.template_filter("currency")
    def currency(value):
        return f"${Decimal(str(value or 0)):,.2f}"

    @app.before_request
    def protect_requests():
        if request.endpoint in {"static", "health"}:
            return None
        if app.config["DEPLOYED"] and (
            not app.config["DEPLOYMENT_SECRET_CONFIGURED"] or not app.config["ADMIN_PASSWORD"]
        ):
            return render_template("setup.html", title="Finish setup"), 503
        if app.config["ADMIN_PASSWORD"] and not session.get("authenticated") and request.endpoint != "login":
            return redirect(url_for("login"))
        if request.method == "POST":
            supplied = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                abort(400, "Your form expired. Reload the page and submit it again.")
        return None

    @app.after_request
    def response_headers(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.errorhandler(ValidationError)
    def invalid_form(error):
        return render_template("error.html", title="Check your form", message=str(error)), 422

    @app.errorhandler(ConfigurationError)
    def missing_settings(error):
        message = "The database connection needs to be configured. Follow SETUP.md in the project."
        if not app.config["DEPLOYED"]:
            message = str(error)
        return render_template("error.html", title="Database setup required", message=message), 503

    @app.errorhandler(mysql.connector.Error)
    def database_error(error):
        app.logger.error("Database request failed (errno=%s).", error.errno)
        if error.errno == 1062:
            message, status = "This record already exists. Check the email, room number, room assignment, or booking review.", 409
        elif error.errno in {1451, 1452}:
            message, status = "A related record is missing, or this record is still referenced by another record.", 409
        elif error.errno in {1205, 1213}:
            message, status = "Another update is in progress. Reload and try again.", 409
        else:
            message, status = "The database is unavailable. Check its connection settings and try again.", 503
        return render_template("error.html", title="Unable to save or load data", message=message), status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("error.html", title=error.name, message=error.description), error.code

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not app.config["ADMIN_PASSWORD"]:
            return redirect(url_for("home"))
        if request.method == "POST":
            actual = hashlib.sha256(request.form.get("password", "").encode()).digest()
            expected = hashlib.sha256(app.config["ADMIN_PASSWORD"].encode()).digest()
            if hmac.compare_digest(actual, expected):
                session.clear()
                session["authenticated"] = True
                session.permanent = True
                return redirect(url_for("home"), code=303)
            return render_template("login.html", title="Staff sign in", login_error=True), 401
        return render_template("login.html", title="Staff sign in")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"), code=303)

    @app.get("/")
    def home():
        today = datetime.now(ZoneInfo(app.config["APP_TIMEZONE"])).date()
        stats = query("""SELECT
            (SELECT COUNT(*) FROM hotels) AS hotels,
            (SELECT COUNT(*) FROM guests) AS guests,
            (SELECT COUNT(*) FROM rooms) AS rooms,
            (SELECT COUNT(*) FROM rooms WHERE room_status='available') AS available_rooms,
            (SELECT COUNT(*) FROM rooms WHERE room_status='occupied') AS occupied_rooms,
            (SELECT COUNT(*) FROM bookings WHERE booking_status IN ('reserved','checked_in')) AS active_bookings,
            (SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_status='paid') AS paid_revenue
        """, one=True)
        occupancy = stats["occupied_rooms"] / stats["rooms"] * 100 if stats["rooms"] else 0
        upcoming = query("""SELECT b.*, p.first_name, p.last_name, h.hotel_name
            FROM bookings b JOIN persons p ON p.person_id=b.guest_id
            JOIN hotels h ON h.hotel_id=b.hotel_id
            WHERE b.check_out_date>=%s AND b.booking_status<>'cancelled'
            ORDER BY b.check_in_date, b.booking_id LIMIT 8""", (today,))
        room_breakdown = query("SELECT room_status AS status,COUNT(*) AS count FROM rooms GROUP BY room_status ORDER BY count DESC")
        booking_breakdown = query("SELECT booking_status AS status,COUNT(*) AS count FROM bookings GROUP BY booking_status ORDER BY count DESC")
        for breakdown in (room_breakdown, booking_breakdown):
            maximum = max((row["count"] for row in breakdown),default=0) or 1
            for row in breakdown:
                row["width"] = round(row["count"] / maximum * 100,2)
        first_month = today.year * 12 + today.month - 1 - 5
        month_dates = [date((first_month+offset)//12,(first_month+offset)%12+1,1) for offset in range(6)]
        paid_months = query("""SELECT DATE_FORMAT(payment_date,'%Y-%m') AS month,SUM(amount) AS revenue
            FROM payments WHERE payment_status='paid' AND payment_date>=%s AND payment_date<=%s
            GROUP BY DATE_FORMAT(payment_date,'%Y-%m') ORDER BY month""", (month_dates[0],today))
        paid_map = {row["month"]:row["revenue"] for row in paid_months}
        revenue = [dict(label=month.strftime("%b %Y"),amount=paid_map.get(month.strftime("%Y-%m"),Decimal("0"))) for month in month_dates]
        maximum = max((month["amount"] for month in revenue),default=0) or 1
        for month in revenue:
            month["height"] = round(float(month["amount"] / maximum) * 100,2)
        return render_template("home.html", title="Overview", stats=stats, upcoming=upcoming,occupancy=occupancy,
                               room_breakdown=room_breakdown,booking_breakdown=booking_breakdown,revenue=revenue)

    def page_rows(sql, params=()):
        try:
            page = max(1, int(request.args.get("page", "1")))
        except ValueError:
            page = 1
        count = query("SELECT COUNT(*) AS total FROM (" + sql + ") AS filtered", params, one=True)["total"]
        pages = max(1, (count + 49) // 50)
        page = min(page, pages)
        rows = query(sql + " LIMIT %s OFFSET %s", (*params, 50, (page - 1) * 50))
        args = request.args.to_dict()
        args.pop("page", None)
        pager = dict(page=page, pages=pages, total=count,
                     previous=url_for(request.endpoint, **args, page=page-1),
                     following=url_for(request.endpoint, **args, page=page+1))
        return rows, pager

    def guest_values():
        values = [text("first_name", 50), text("last_name", 50), text("email", 100),
                  text("phone", 20), integer("age", 18, 120), text("street_address", 150),
                  text("city", 80), text("state_province", 80), text("zip_code", 20)]
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values[2]):
            raise ValidationError("Enter a valid email address.")
        return values, choice("guest_status", GUEST_STATUS), choice("loyalty_level", LOYALTY)

    @app.route("/guests/new", methods=["GET", "POST"])
    def guests_new():
        if request.method == "POST":
            values, status, loyalty = guest_values()
            with transaction():
                person_id = execute("""INSERT INTO persons
                    (first_name,last_name,email,phone,age,street_address,city,state_province,zip_code)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)
                execute("INSERT INTO guests (guest_id,guest_status,loyalty_level) VALUES (%s,%s,%s)", (person_id,status,loyalty))
            flash("Guest added successfully.", "success")
            return redirect(url_for("guests"), code=303)
        return render_template("guest_form.html", title="Add guest", guest={})

    @app.route("/guests", methods=["GET", "POST"])
    def guests():
        if request.method == "POST":
            choice("action", ("delete",))
            guest_id = integer("guest_id")
            with transaction():
                if not query("SELECT guest_id FROM guests WHERE guest_id=%s FOR UPDATE", (guest_id,), one=True):
                    abort(404, "Guest not found.")
                execute("DELETE FROM guests WHERE guest_id=%s", (guest_id,))
                # Shared person records must survive if this guest is also staff.
                execute("DELETE FROM persons WHERE person_id=%s AND NOT EXISTS (SELECT 1 FROM staff WHERE staff_id=%s)", (guest_id,guest_id))
            flash("Guest deleted.", "success")
            return redirect(url_for("guests"), code=303)
        sql = "SELECT p.*, g.guest_id, g.guest_status, g.loyalty_level FROM guests g JOIN persons p ON p.person_id=g.guest_id WHERE 1=1"
        params = []
        if request.args.get("search"):
            sql += " AND (p.first_name LIKE %s OR p.last_name LIKE %s)"
            params.extend(["%"+request.args["search"]+"%"] * 2)
        for field, options in [("guest_status",GUEST_STATUS),("loyalty_level",LOYALTY)]:
            if request.args.get(field) in options:
                sql += f" AND g.{field}=%s"
                params.append(request.args[field])
        rows, pager = page_rows(sql + " ORDER BY g.guest_id DESC", params)
        return render_template("guests.html", title="Guests", rows=rows, pager=pager)

    @app.route("/guests/<int:guest_id>/edit", methods=["GET", "POST"])
    def guests_edit(guest_id):
        guest = query("SELECT p.*,g.guest_status,g.loyalty_level FROM guests g JOIN persons p ON p.person_id=g.guest_id WHERE guest_id=%s", (guest_id,), one=True)
        if not guest:
            abort(404, "Guest not found.")
        if request.method == "POST":
            values, status, loyalty = guest_values()
            with transaction():
                if not query("SELECT guest_id FROM guests WHERE guest_id=%s FOR UPDATE", (guest_id,), one=True):
                    abort(404, "Guest not found.")
                execute("""UPDATE persons SET first_name=%s,last_name=%s,email=%s,phone=%s,age=%s,
                    street_address=%s,city=%s,state_province=%s,zip_code=%s WHERE person_id=%s""", (*values,guest_id))
                execute("UPDATE guests SET guest_status=%s,loyalty_level=%s WHERE guest_id=%s", (status,loyalty,guest_id))
            flash("Guest updated.", "success")
            return redirect(url_for("guests"), code=303)
        return render_template("guest_form.html", title="Edit guest", guest=guest)

    @app.route("/hotels", methods=["GET", "POST"])
    def hotels():
        if request.method == "POST":
            values = [text("hotel_name",100), text("contact_phone",20), text("street_address",150),
                      text("city",80), text("state_province",80), text("zip_code",20),
                      money("star_rating",minimum=Decimal("1"),maximum=Decimal("5"))]
            if values[-1] * 2 != int(values[-1] * 2):
                raise ValidationError("Star rating must use half-star increments.")
            with transaction():
                execute("""INSERT INTO hotels (hotel_name,contact_phone,street_address,city,state_province,zip_code,star_rating)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""", values)
            flash("Hotel added.", "success")
            return redirect(url_for("hotels"), code=303)
        rows, pager = page_rows("SELECT * FROM hotels ORDER BY hotel_id DESC")
        return render_template("hotels.html", title="Hotels", rows=rows, pager=pager)

    @app.route("/rooms/new", methods=["GET", "POST"])
    def rooms_new():
        if request.method == "POST":
            action = choice("action", ("room_type", "room"))
            if action == "room_type":
                values = (text("type_name",50),integer("capacity"),money("base_price"))
                with transaction():
                    execute("INSERT INTO room_types (type_name,capacity,base_price) VALUES (%s,%s,%s)", values)
                flash("Room type added.", "success")
            else:
                values = (integer("hotel_id"),integer("room_type_id"),text("room_number",20),choice("room_status",ROOM_STATUS))
                with transaction():
                    execute("INSERT INTO rooms (hotel_id,room_type_id,room_number,room_status) VALUES (%s,%s,%s,%s)", values)
                flash("Room added.", "success")
            return redirect(url_for("rooms_new"), code=303)
        return render_template("room_form.html", title="Add room", hotels=query("SELECT hotel_id,hotel_name FROM hotels ORDER BY hotel_name"),
                               room_types=query("SELECT * FROM room_types ORDER BY type_name"))

    @app.route("/rooms", methods=["GET", "POST"])
    def rooms():
        if request.method == "POST":
            room_id, status = integer("room_id"), choice("room_status",ROOM_STATUS)
            with transaction():
                if not query("SELECT room_id FROM rooms WHERE room_id=%s FOR UPDATE", (room_id,), one=True):
                    abort(404, "Room not found.")
                execute("UPDATE rooms SET room_status=%s WHERE room_id=%s", (status,room_id))
            flash("Room status updated.", "success")
            return redirect(url_for("rooms"), code=303)
        sql = """SELECT r.*,h.hotel_name,rt.type_name,rt.capacity,rt.base_price FROM rooms r
            JOIN hotels h ON h.hotel_id=r.hotel_id JOIN room_types rt ON rt.room_type_id=r.room_type_id WHERE 1=1"""
        params = []
        hotel_id = positive_filter("hotel_id")
        if hotel_id is not None:
            sql += " AND r.hotel_id=%s"
            params.append(hotel_id)
        if request.args.get("room_status") in ROOM_STATUS:
            sql += " AND r.room_status=%s"
            params.append(request.args["room_status"])
        if request.args.get("search"):
            sql += " AND rt.type_name LIKE %s"
            params.append("%"+request.args["search"]+"%")
        rows, pager = page_rows(sql + " ORDER BY r.room_id DESC", params)
        return render_template("rooms.html", title="Rooms", rows=rows,pager=pager,
                               hotels=query("SELECT hotel_id,hotel_name FROM hotels ORDER BY hotel_name"))

    register_booking_routes(app, page_rows)
    return app


def register_booking_routes(app, page_rows):
    def check_room(booking, room_id):
        room = query("SELECT * FROM rooms WHERE room_id=%s FOR UPDATE", (room_id,), one=True)
        if not room:
            raise ValidationError("The selected room does not exist.")
        if room["hotel_id"] != booking["hotel_id"]:
            raise ValidationError("Choose a room belonging to the booking's hotel.")
        if room["room_status"] in {"maintenance", "cleaning"}:
            raise ValidationError("This room is unavailable while it is in maintenance or cleaning.")
        # The room lock serializes assignments. A locking read uses the current
        # committed state even after waiting for another transaction's lock.
        overlap = query("""SELECT b.booking_id FROM booking_rooms br
            JOIN bookings b ON b.booking_id=br.booking_id
            WHERE br.room_id=%s AND b.booking_id<>%s
              AND b.booking_status IN ('reserved','checked_in')
              AND b.check_in_date<%s AND b.check_out_date>%s FOR UPDATE""",
            (room_id, booking["booking_id"], booking["check_out_date"], booking["check_in_date"]), one=True)
        if overlap:
            raise ValidationError("This room already has a booking for those dates.")

    def assign_room(booking, room_id, rate):
        if booking["booking_status"] not in ACTIVE_BOOKINGS:
            raise ValidationError("Rooms can be assigned to reserved or checked-in bookings.")
        check_room(booking, room_id)
        execute("INSERT INTO booking_rooms (booking_id,room_id,agreed_nightly_rate) VALUES (%s,%s,%s)",
                (booking["booking_id"],room_id,rate))

    @app.route("/bookings/new", methods=["GET", "POST"])
    def bookings_new():
        if request.method == "POST":
            guest_id, hotel_id = integer("guest_id"), integer("hotel_id")
            booking_date, check_in, check_out = day("booking_date"), day("check_in_date"), day("check_out_date")
            status = choice("booking_status",BOOKING_STATUS)
            room_id = integer("room_id",minimum=0,default=0)
            rate = money("nightly_rate") if room_id else None
            if check_out <= check_in:
                raise ValidationError("Check-out must be after check-in.")
            if booking_date > check_in:
                raise ValidationError("Booking date must be on or before check-in.")
            with transaction():
                booking_id = execute("""INSERT INTO bookings
                    (guest_id,hotel_id,booking_date,check_in_date,check_out_date,booking_status)
                    VALUES (%s,%s,%s,%s,%s,%s)""", (guest_id,hotel_id,booking_date,check_in,check_out,status))
                if room_id:
                    booking = dict(booking_id=booking_id,hotel_id=hotel_id,check_in_date=check_in,
                                   check_out_date=check_out,booking_status=status)
                    assign_room(booking,room_id,rate)
            flash(f"Booking #{booking_id} created.", "success")
            return redirect(url_for("bookings"), code=303)
        guests = query("SELECT g.guest_id,p.first_name,p.last_name FROM guests g JOIN persons p ON p.person_id=g.guest_id ORDER BY p.last_name,p.first_name")
        hotels = query("SELECT hotel_id,hotel_name FROM hotels ORDER BY hotel_name")
        rooms = query("""SELECT r.room_id,r.hotel_id,r.room_number,h.hotel_name,rt.type_name,rt.base_price
            FROM rooms r JOIN hotels h ON h.hotel_id=r.hotel_id
            JOIN room_types rt ON rt.room_type_id=r.room_type_id
            WHERE r.room_status NOT IN ('maintenance','cleaning') ORDER BY h.hotel_name,r.room_number""")
        return render_template("booking_form.html",title="New booking",guests=guests,hotels=hotels,rooms=rooms)

    @app.route("/bookings", methods=["GET", "POST"])
    def bookings():
        if request.method == "POST":
            action = choice("action", ("status", "assign"))
            booking_id = integer("booking_id")
            with transaction():
                booking = query("SELECT * FROM bookings WHERE booking_id=%s FOR UPDATE", (booking_id,), one=True)
                if not booking:
                    abort(404,"Booking not found.")
                if action == "status":
                    status = choice("booking_status",BOOKING_STATUS)
                    if status in ACTIVE_BOOKINGS:
                        # Reopening a cancelled/completed booking must not
                        # introduce overlaps with newer room reservations.
                        for room in query("SELECT room_id FROM booking_rooms WHERE booking_id=%s ORDER BY room_id", (booking_id,)):
                            check_room(booking,room["room_id"])
                    execute("UPDATE bookings SET booking_status=%s WHERE booking_id=%s", (status,booking_id))
                else:
                    assign_room(booking,integer("room_id"),money("nightly_rate"))
            flash("Booking status updated." if action == "status" else "Room assigned to booking.", "success")
            return redirect(url_for("bookings"),code=303)
        sql = """SELECT b.*,p.first_name,p.last_name,h.hotel_name,
            assignments.room_numbers,
            DATEDIFF(b.check_out_date,b.check_in_date)*COALESCE(assignments.nightly_rate,0) AS total_cost
            FROM bookings b JOIN persons p ON p.person_id=b.guest_id JOIN hotels h ON h.hotel_id=b.hotel_id
            LEFT JOIN (SELECT br.booking_id,GROUP_CONCAT(r.room_number ORDER BY r.room_number SEPARATOR ', ') AS room_numbers,
                       SUM(br.agreed_nightly_rate) AS nightly_rate FROM booking_rooms br
                       JOIN rooms r ON r.room_id=br.room_id GROUP BY br.booking_id) assignments ON assignments.booking_id=b.booking_id
            WHERE 1=1"""
        params = []
        if request.args.get("booking_status") in BOOKING_STATUS:
            sql += " AND b.booking_status=%s"
            params.append(request.args["booking_status"])
        if request.args.get("search"):
            sql += " AND (p.first_name LIKE %s OR p.last_name LIKE %s)"
            params.extend(["%"+request.args["search"]+"%"] * 2)
        rows,pager = page_rows(sql + " ORDER BY b.booking_id DESC",params)
        return render_template("bookings.html",title="Bookings",rows=rows,pager=pager)

    @app.route("/payments", methods=["GET", "POST"])
    def payments():
        if request.method == "POST":
            values = (integer("booking_id"),day("payment_date"),money("amount"),
                      choice("payment_method",PAYMENT_METHOD),choice("payment_status",PAYMENT_STATUS))
            with transaction():
                if not query("SELECT booking_id FROM bookings WHERE booking_id=%s", (values[0],),one=True):
                    raise ValidationError("Booking not found.")
                execute("""INSERT INTO payments (booking_id,payment_date,amount,payment_method,payment_status)
                    VALUES (%s,%s,%s,%s,%s)""",values)
            flash("Payment recorded.","success")
            return redirect(url_for("payments"),code=303)
        sql = """SELECT pay.*,p.first_name,p.last_name FROM payments pay
            JOIN bookings b ON b.booking_id=pay.booking_id JOIN persons p ON p.person_id=b.guest_id WHERE 1=1"""
        params = []
        booking_id = positive_filter("booking_id")
        if booking_id is not None:
            sql += " AND pay.booking_id=%s"
            params.append(booking_id)
        if request.args.get("payment_status") in PAYMENT_STATUS:
            sql += " AND pay.payment_status=%s"
            params.append(request.args["payment_status"])
        paid = query("SELECT COALESCE(SUM(amount),0) AS total FROM (" + sql + ") filtered WHERE payment_status='paid'",params,one=True)["total"]
        rows,pager = page_rows(sql + " ORDER BY pay.payment_id DESC",params)
        return render_template("payments.html",title="Payments",rows=rows,pager=pager,total_paid=paid)

    @app.route("/reviews", methods=["GET", "POST"])
    def reviews():
        if request.method == "POST":
            values = (integer("booking_id"),integer("rating",1,5),text("review_text",5000,optional=True) or None,day("review_date"))
            with transaction():
                booking = query("SELECT booking_id,booking_status FROM bookings WHERE booking_id=%s FOR UPDATE",(values[0],),one=True)
                if not booking:
                    raise ValidationError("Booking not found.")
                if booking["booking_status"] != "checked_out":
                    raise ValidationError("Mark this booking as checked out before adding a review.")
                execute("INSERT INTO reviews (booking_id,rating,review_text,review_date) VALUES (%s,%s,%s,%s)",values)
            flash("Review added.","success")
            return redirect(url_for("reviews"),code=303)
        try:
            minimum = max(1,min(5,int(request.args.get("rating","1"))))
        except ValueError:
            minimum = 1
        sql = """SELECT rv.*,p.first_name,p.last_name,h.hotel_name FROM reviews rv
            JOIN bookings b ON b.booking_id=rv.booking_id JOIN persons p ON p.person_id=b.guest_id
            JOIN hotels h ON h.hotel_id=b.hotel_id WHERE rv.rating>=%s"""
        params = [minimum]
        if request.args.get("search"):
            sql += " AND h.hotel_name LIKE %s"
            params.append("%"+request.args["search"]+"%")
        average = query("SELECT COALESCE(AVG(rating),0) AS average FROM (" + sql + ") filtered",params,one=True)["average"]
        rows,pager = page_rows(sql + " ORDER BY rv.review_id DESC",params)
        return render_template("reviews.html",title="Reviews",rows=rows,pager=pager,average=average)


app = create_app()
