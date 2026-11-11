"""Run against a temporary MySQL database; never modifies the source database."""

from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch

import mysql.connector
from flask import template_rendered

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app as application
import manage
import db_connection


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = application.create_app({"TESTING":True,"SECRET_KEY":"test-secret","ADMIN_PASSWORD":"test-password","DEPLOYED":False})
        self.client = self.app.test_client()

    def token(self):
        response = self.client.get("/login")
        return re.search(rb'name="csrf_token" value="([^"]+)"',response.data)[1].decode()

    def test_login_is_required_and_bad_password_is_rejected(self):
        self.assertEqual(self.client.get("/guests").status_code,302)
        response = self.client.post("/login",data={"csrf_token":self.token(),"password":"wrong"})
        self.assertEqual(response.status_code,401)

    def test_login_rotates_session_and_logout_requires_csrf(self):
        token = self.token()
        response = self.client.post("/login",data={"csrf_token":token,"password":"test-password"})
        self.assertEqual(response.status_code,303)
        with self.client.session_transaction() as session:
            self.assertTrue(session["authenticated"])
            self.assertNotIn("csrf_token",session)
        self.assertEqual(self.client.post("/logout").status_code,400)

    def test_non_ascii_csrf_is_rejected_without_crashing(self):
        self.token()
        self.assertEqual(self.client.post("/login",data={"csrf_token":"非ASCII","password":"test-password"}).status_code,400)

    def test_production_requires_password_and_stable_session_secret(self):
        app = application.create_app({"TESTING":True,"DEPLOYED":True,"DEPLOYMENT_SECRET_CONFIGURED":False,"ADMIN_PASSWORD":""})
        self.assertEqual(app.test_client().get("/").status_code,503)

    def test_health_and_stylesheet_are_available(self):
        response = self.client.get("/health")
        self.assertEqual(response.json,{"status":"ok"})
        with self.client.get("/style.css") as stylesheet:
            self.assertEqual(stylesheet.status_code,200)
        self.assertEqual(self.client.get("/login").headers["Cache-Control"],"no-store")

    def test_cloud_database_settings_include_verified_tls(self):
        environment=dict(VERCEL="1",MYSQL_HOST="test.tidbcloud.com",MYSQL_PORT="4000",MYSQL_USER="test-user",MYSQL_PASSWORD="test-password",MYSQL_DATABASE="test")
        with patch.dict(os.environ,environment,clear=True):
            settings=db_connection.connection_settings()
        self.assertEqual(settings["port"],4000)
        self.assertTrue(settings["ssl_verify_cert"])
        self.assertTrue(settings["ssl_verify_identity"])
        self.assertTrue(Path(settings["ssl_ca"]).is_file())
        for changes in [{"MYSQL_HOST":"localhost"},{"MYSQL_SSL_VERIFY":"false"},{"MYSQL_PORT":"invalid"}]:
            with self.subTest(changes=changes),patch.dict(os.environ,{**environment,**changes},clear=True):
                with self.assertRaises(db_connection.ConfigurationError):
                    db_connection.connection_settings()

    def test_partial_cloud_settings_never_mix_with_local_credentials(self):
        with patch.dict(os.environ,{"MYSQL_HOST":"test.tidbcloud.com"},clear=True):
            with self.assertRaisesRegex(db_connection.ConfigurationError,"MYSQL_PASSWORD"):
                db_connection.connection_settings()

    def test_local_toml_credentials_do_not_require_streamlit(self):
        with tempfile.NamedTemporaryFile(mode="w",suffix=".toml") as handle:
            handle.write('[mysql]\nhost="localhost"\nuser="test"\npassword=""\ndatabase="test"\n')
            handle.flush()
            with patch.dict(os.environ,{"HMS_LOCAL_SECRETS_FILE":handle.name},clear=True):
                settings=db_connection.connection_settings()
        self.assertEqual(settings["host"],"localhost")
        self.assertFalse(settings["ssl_verify_cert"])

    def test_custom_ca_file_is_cleaned_up_after_connector_handshake(self):
        environment=dict(MYSQL_HOST="test.tidbcloud.com",MYSQL_USER="test-user",MYSQL_PASSWORD="test-password",MYSQL_DATABASE="test",MYSQL_SSL_CA_PEM="test-certificate")
        paths=[]
        def connect(**settings):
            paths.append(Path(settings["ssl_ca"]))
            self.assertEqual(paths[0].read_text(),"test-certificate")
            return "test-connection"
        with patch.dict(os.environ,environment,clear=True),patch.object(db_connection.mysql.connector,"connect",side_effect=connect):
            self.assertEqual(db_connection.get_connection(),"test-connection")
        self.assertFalse(paths[0].exists())


@unittest.skipUnless(os.environ.get("HMS_TEST_SECRETS_FILE"),"Set HMS_TEST_SECRETS_FILE for isolated MySQL integration tests.")
class MySQLWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Path(os.environ["HMS_TEST_SECRETS_FILE"]).open("rb") as handle:
            settings = tomllib.load(handle)["mysql"]
        cls.settings = {key:settings[key] for key in ["host","user","password"]}
        cls.settings.update(port=int(settings.get("port",3306)),autocommit=True,connection_timeout=5)
        cls.database = "hms_codex_test_"+secrets.token_hex(5)
        cls.admin = mysql.connector.connect(**cls.settings)
        cls.settings["database"] = cls.database
        cursor = cls.admin.cursor()
        cursor.execute(f"CREATE DATABASE `{cls.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        try:
            with mysql.connector.connect(**cls.settings) as connection:
                cursor = connection.cursor()
                schema = re.sub(r"--[^\n]*", "", (ROOT/"schema.mysql.sql").read_text())
                for statement in schema.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
                cursor.close()
        except BaseException:
            cursor=cls.admin.cursor()
            cursor.execute(f"DROP DATABASE `{cls.database}`")
            cursor.close()
            cls.admin.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cursor=cls.admin.cursor()
        cursor.execute(f"DROP DATABASE `{cls.database}`")
        cursor.close()
        cls.admin.close()

    def setUp(self):
        self.connection = mysql.connector.connect(**self.settings)
        cursor=self.connection.cursor()
        for table in ["reviews","payments","booking_rooms","bookings","rooms","room_types","staff","staff_roles","guests","persons","hotels"]:
            cursor.execute(f"DELETE FROM {table}")
        cursor.close()
        self.app=application.create_app({"TESTING":True,"SECRET_KEY":"integration-test-secret","ADMIN_PASSWORD":"test-password",
            "DEPLOYED":False,"DATABASE_CONNECT":lambda:mysql.connector.connect(**self.settings)})
        self.client=self.app.test_client()
        token=re.search(rb'name="csrf_token" value="([^"]+)"',self.client.get("/login").data)[1].decode()
        self.client.post("/login",data={"csrf_token":token,"password":"test-password"})

    def tearDown(self):
        self.connection.close()

    def sql(self,statement,params=(),one=False):
        cursor=self.connection.cursor(dictionary=True,buffered=True)
        try:
            cursor.execute(statement,params)
            if cursor.with_rows:
                return cursor.fetchone() if one else cursor.fetchall()
            return cursor.lastrowid
        finally:
            cursor.close()

    def count(self,table):
        return self.sql(f"SELECT COUNT(*) AS total FROM {table}",one=True)["total"]

    def post(self,url,**data):
        with self.client.session_transaction() as session:
            session.setdefault("csrf_token",secrets.token_urlsafe(32))
            token=session["csrf_token"]
        return self.client.post(url,data={**data,"csrf_token":token})

    def guest_data(self,**changes):
        return dict(first_name="Ada",last_name="Lovelace",email="ada@example.test",phone="12345",age="30",
            street_address="1 Test Street",city="Test City",state_province="Test Province",zip_code="12345",
            guest_status="active",loyalty_level="gold",**changes)

    def seed(self):
        hotel=self.sql("INSERT INTO hotels (hotel_name,contact_phone,street_address,city,state_province,zip_code,star_rating) VALUES ('Test Hotel','123','1 Test Street','Test','Province','123',3)")
        room_type=self.sql("INSERT INTO room_types (type_name,capacity,base_price) VALUES ('Suite',2,100)")
        room=self.sql("INSERT INTO rooms (hotel_id,room_type_id,room_number) VALUES (%s,%s,'101')",(hotel,room_type))
        person=self.sql("INSERT INTO persons (first_name,last_name,email,phone,age,street_address,city,state_province,zip_code) VALUES ('Ada','Lovelace','ada@example.test','123',30,'1 Test Street','Test','Province','123')")
        self.sql("INSERT INTO guests (guest_id) VALUES (%s)",(person,))
        return hotel,room_type,room,person

    def booking_data(self,hotel,room,guest,**changes):
        data=dict(guest_id=guest,hotel_id=hotel,room_id=room,nightly_rate="150.00",booking_date="2030-01-01",
            check_in_date="2030-01-02",check_out_date="2030-01-05",booking_status="reserved")
        data.update(changes)
        return data

    def test_all_pages_render_on_empty_database(self):
        for url in ["/","/guests/new","/guests","/hotels","/rooms/new","/rooms","/bookings/new","/bookings","/payments","/reviews"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code,200)

    def test_dashboard_preserves_occupancy_status_and_monthly_paid_revenue(self):
        hotel,room_type,room,guest=self.seed()
        self.sql("INSERT INTO rooms (hotel_id,room_type_id,room_number,room_status) VALUES (%s,%s,'102','occupied')",(hotel,room_type))
        self.post("/bookings/new",**self.booking_data(hotel,room,guest))
        booking=self.sql("SELECT booking_id FROM bookings",one=True)["booking_id"]
        for payment_date,amount,status in [("2026-06-01","123.45","paid"),("2026-11-09","76.55","paid"),("2026-05-31","50.00","paid"),("2026-11-09","999.00","pending")]:
            self.sql("INSERT INTO payments (booking_id,payment_date,amount,payment_method,payment_status) VALUES (%s,%s,%s,'cash',%s)",(booking,payment_date,amount,status))
        captured=[]
        def record(_sender,template,context,**extra):
            captured.append(context)
        with patch.object(application,"datetime") as clock,template_rendered.connected_to(record,self.app):
            clock.now.return_value=datetime(2026,11,10)
            response=self.client.get("/")
        self.assertEqual(response.status_code,200)
        context=captured[0]
        self.assertEqual(context["occupancy"],50)
        self.assertEqual(context["stats"]["available_rooms"],1)
        self.assertEqual(str(context["stats"]["paid_revenue"]),"250.00")
        self.assertEqual(sum(row["count"] for row in context["room_breakdown"]),2)
        self.assertEqual(sum(row["count"] for row in context["booking_breakdown"]),1)
        self.assertEqual([row["label"] for row in context["revenue"]],["Jun 2026","Jul 2026","Aug 2026","Sep 2026","Oct 2026","Nov 2026"])
        self.assertEqual(str(context["revenue"][0]["amount"]),"123.45")
        self.assertEqual(str(context["revenue"][-1]["amount"]),"76.55")
        self.assertNotIn(b"$999.00",response.data)

    def test_complete_hotel_guest_booking_payment_review_workflow(self):
        response=self.post("/hotels",hotel_name="Grand Test",contact_phone="123",street_address="1 Test Street",city="Test",state_province="Province",zip_code="123",star_rating="4.5")
        self.assertEqual(response.status_code,303)
        hotel=self.sql("SELECT hotel_id FROM hotels",one=True)["hotel_id"]
        self.assertEqual(self.post("/rooms/new",action="room_type",type_name="Suite",capacity=2,base_price="150.00").status_code,303)
        room_type=self.sql("SELECT room_type_id FROM room_types",one=True)["room_type_id"]
        self.assertEqual(self.post("/rooms/new",action="room",hotel_id=hotel,room_type_id=room_type,room_number="101",room_status="available").status_code,303)
        room=self.sql("SELECT room_id FROM rooms",one=True)["room_id"]
        self.assertEqual(self.post("/guests/new",**self.guest_data()).status_code,303)
        guest=self.sql("SELECT guest_id FROM guests",one=True)["guest_id"]
        self.assertEqual(self.post(f"/guests/{guest}/edit",**self.guest_data()).status_code,303)
        self.assertEqual(self.post("/bookings/new",**self.booking_data(hotel,room,guest)).status_code,303)
        booking=self.sql("SELECT booking_id FROM bookings",one=True)["booking_id"]
        self.assertIn(b"$450.00",self.client.get("/bookings").data)
        self.assertEqual(self.post("/payments",booking_id=booking,payment_date="2030-01-02",amount="450.00",payment_method="credit_card",payment_status="paid").status_code,303)
        self.assertIn(b"$450.00",self.client.get("/payments").data)
        self.assertEqual(self.post("/bookings",action="status",booking_id=booking,booking_status="checked_out").status_code,303)
        review=dict(booking_id=booking,rating=5,review_date="2030-01-05",review_text="<script>alert('test')</script>")
        self.assertEqual(self.post("/reviews",**review).status_code,303)
        self.assertIn(b"&lt;script&gt;",self.client.get("/reviews").data)
        self.assertEqual(self.post("/reviews",**review).status_code,409)
        self.assertEqual(self.count("reviews"),1)
        self.assertEqual(self.post("/rooms",room_id=room,room_status="cleaning").status_code,303)

    def test_wrong_hotel_room_rolls_back_whole_booking(self):
        hotel,_type,room,guest=self.seed()
        other=self.sql("INSERT INTO hotels (hotel_name,contact_phone,street_address,city,state_province,zip_code) VALUES ('Other','123','Street','City','State','123')")
        response=self.post("/bookings/new",**self.booking_data(other,room,guest))
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.count("bookings"),0)
        self.assertEqual(self.count("booking_rooms"),0)

    def test_overlapping_bookings_rejected_but_adjacent_dates_allowed(self):
        hotel,_type,room,guest=self.seed()
        data=self.booking_data(hotel,room,guest)
        self.assertEqual(self.post("/bookings/new",**data).status_code,303)
        self.assertEqual(self.post("/bookings/new",**data).status_code,422)
        self.assertEqual(self.count("bookings"),1)
        data.update(check_in_date="2030-01-05",check_out_date="2030-01-07")
        self.assertEqual(self.post("/bookings/new",**data).status_code,303)

    def test_concurrent_requests_cannot_double_book_a_room(self):
        hotel,_type,room,guest=self.seed()
        data=self.booking_data(hotel,room,guest)
        barrier=threading.Barrier(2)
        def create_booking(_index):
            client=self.app.test_client()
            token=secrets.token_urlsafe(32)
            with client.session_transaction() as session:
                session["authenticated"]=True
                session["csrf_token"]=token
            barrier.wait(timeout=5)
            return client.post("/bookings/new",data={**data,"csrf_token":token}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses=list(executor.map(create_booking,range(2)))
        self.assertEqual(statuses.count(303),1,statuses)
        self.assertTrue(all(status in {303,409,422} for status in statuses),statuses)
        self.assertEqual(self.count("bookings"),1)

    def test_reopening_cancelled_booking_rechecks_overlaps(self):
        hotel,_type,room,guest=self.seed()
        data=self.booking_data(hotel,room,guest)
        self.post("/bookings/new",**data)
        first=self.sql("SELECT booking_id FROM bookings",one=True)["booking_id"]
        self.post("/bookings",action="status",booking_id=first,booking_status="cancelled")
        self.assertEqual(self.post("/bookings/new",**data).status_code,303)
        self.assertEqual(self.post("/bookings",action="status",booking_id=first,booking_status="reserved").status_code,422)
        self.assertEqual(self.sql("SELECT booking_status FROM bookings WHERE booking_id=%s",(first,),one=True)["booking_status"],"cancelled")

    def test_guest_and_person_creation_roll_back_together(self):
        original=application.execute
        def fail_second_insert(sql,params=()):
            if "INSERT INTO guests" in sql:
                raise mysql.connector.DatabaseError("injected failure")
            return original(sql,params)
        with patch.object(application,"execute",side_effect=fail_second_insert):
            self.assertEqual(self.post("/guests/new",**self.guest_data()).status_code,503)
        self.assertEqual(self.count("persons"),0)
        self.assertEqual(self.count("guests"),0)

    def test_duplicate_email_leaves_no_orphan_person(self):
        self.post("/guests/new",**self.guest_data())
        self.assertEqual(self.post("/guests/new",**self.guest_data()).status_code,409)
        self.assertEqual(self.count("persons"),1)
        self.assertEqual(self.count("guests"),1)

    def test_invalid_dates_amounts_and_missing_ids(self):
        hotel,_type,room,guest=self.seed()
        data=self.booking_data(hotel,room,guest,check_out_date="2030-01-01")
        self.assertEqual(self.post("/bookings/new",**data).status_code,422)
        for amount in ["NaN","Infinity","-1","1.001"]:
            with self.subTest(amount=amount):
                self.assertEqual(self.post("/payments",booking_id=1,payment_date="2030-01-02",amount=amount,payment_method="cash",payment_status="paid").status_code,422)
        self.assertEqual(self.post("/rooms",room_id=2147483647,room_status="available").status_code,404)
        self.assertEqual(self.client.get("/guests/2147483647/edit").status_code,404)
        self.assertEqual(self.client.get("/rooms?hotel_id=%C2%B2").status_code,200)
        self.assertEqual(self.client.get("/payments?booking_id="+"9"*100).status_code,200)
        self.assertEqual(self.count("bookings"),0)
        self.assertEqual(self.count("payments"),0)

    def test_guest_with_booking_cannot_be_deleted(self):
        hotel,_type,room,guest=self.seed()
        self.post("/bookings/new",**self.booking_data(hotel,room,guest))
        self.assertEqual(self.post("/guests",action="delete",guest_id=guest).status_code,409)
        self.assertEqual(self.count("guests"),1)
        self.assertEqual(self.count("persons"),1)

    def test_deleting_guest_preserves_shared_staff_record(self):
        hotel,_type,_room,guest=self.seed()
        role=self.sql("INSERT INTO staff_roles (role_name) VALUES ('Reception')")
        self.sql("INSERT INTO staff (staff_id,hotel_id,staff_role_id,salary) VALUES (%s,%s,%s,1000)",(guest,hotel,role))
        self.assertEqual(self.post("/guests",action="delete",guest_id=guest).status_code,303)
        self.assertEqual(self.count("guests"),0)
        self.assertEqual(self.count("staff"),1)
        self.assertEqual(self.count("persons"),1)

    def test_search_is_parameterized_and_pagination_is_complete(self):
        self.seed()
        self.assertEqual(self.client.get("/guests?search=%27%20OR%201=1%20--").status_code,200)
        self.assertIn(b"No guests match",self.client.get("/guests?search=%27%20OR%201=1%20--").data)
        for index in range(51):
            person=self.sql("INSERT INTO persons (first_name,last_name,email,phone,age,street_address,city,state_province,zip_code) VALUES (%s,'Test',%s,'123',30,'Street','City','State','123')",(f"Guest{index}",f"guest{index}@example.test"))
            self.sql("INSERT INTO guests (guest_id) VALUES (%s)",(person,))
        first=self.client.get("/guests")
        second=self.client.get("/guests?page=2")
        self.assertEqual(first.data.count(b"<tr>"),51)
        self.assertEqual(second.data.count(b"<tr>"),3)
        self.assertIn(b"52 records",first.data)

    def test_database_initializer_refuses_existing_tables(self):
        self.seed()
        with self.assertRaisesRegex(ValueError,"empty database"):
            manage.initialize_database(self.connection)
        self.assertEqual(self.count("guests"),1)

    def test_data_copy_preserves_ids_and_refuses_overwriting_target(self):
        hotel,room_type,room,guest=self.seed()
        self.post("/bookings/new",**self.booking_data(hotel,room,guest))
        role=self.sql("INSERT INTO staff_roles (role_name) VALUES ('Reception')")
        self.sql("INSERT INTO staff (staff_id,hotel_id,staff_role_id,salary) VALUES (%s,%s,%s,1000)",(guest,hotel,role))
        name="hms_codex_test_"+secrets.token_hex(5)
        cursor=self.admin.cursor()
        cursor.execute(f"CREATE DATABASE `{name}`")
        cursor.close()
        target=mysql.connector.connect(**{**self.settings,"database":name})
        try:
            manage.initialize_database(target)
            counts=manage.copy_data(self.connection,target)
            self.assertEqual(counts["guests"],1)
            self.assertEqual(counts["bookings"],1)
            self.assertEqual(counts["staff"],1)
            cursor=target.cursor()
            cursor.execute("SELECT guest_id FROM guests")
            self.assertEqual(cursor.fetchone()[0],guest)
            cursor.close()
            with self.assertRaisesRegex(ValueError,"empty application tables"):
                manage.copy_data(self.connection,target)
            self.assertEqual(self.count("bookings"),1)
        finally:
            target.close()
            cursor=self.admin.cursor()
            cursor.execute(f"DROP DATABASE `{name}`")
            cursor.close()


if __name__=="__main__":
    unittest.main()
