# Hotel Management System

A hotel management web application built with Flask, HTML forms, and MySQL
Connector/Python. It runs locally or on Vercel and supports a hosted MySQL or
MySQL-compatible TiDB Cloud database.

## Included features

- Dashboard with occupancy, available rooms, active reservations, and paid revenue
- Upcoming stays, room and reservation status charts, and six-month paid revenue
- Add, search, filter, edit, and delete guests
- Add and view hotels, room types, and rooms; update room status
- Create bookings, assign rooms, filter reservations, and update booking status
- Record and filter payments, including totals for paid records
- Add and view reviews, one per completed booking
- Staff password sign-in, protected forms, responsive pages, and pagination

All eleven original database tables are preserved, including staff and staff
roles. Staff management screens were not part of the original application.
The application records payment details; it does not process card charges.

## Start here

Follow [SETUP.md](SETUP.md) to create the free TiDB Cloud MySQL-compatible
database, connect Vercel, and optionally copy your existing records.

## Run against your existing local database

Use Python 3.12 or newer. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example and edit `.streamlit/secrets.toml` with your local database
credentials. The application reads its `[mysql]` section as TOML:

```sh
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
python3 -m flask --app app run --port 5000
```

Then open http://localhost:5000. This uses your existing local hotel database, so
saving a form changes that database. No database setup or migration runs when
the app starts. Set `ADMIN_PASSWORD` to enable staff sign-in locally too.
To reuse an existing credentials file, set `HMS_LOCAL_SECRETS_FILE` to that
file's absolute path instead of copying the example.

In Vercel, `SECRET_KEY`, `ADMIN_PASSWORD`, and the hosted `MYSQL_*` settings are
required. Vercel serves static assets from `public/` and detects `app.py` as the
Flask entry point. No build command or output directory is needed.

## Behavior strengthened during conversion

Guest/person creation and booking/room assignment each save as a transaction.
Rooms must belong to the reservation's hotel and cannot overlap another active
booking. Reopening a cancelled reservation rechecks availability. A guest who
is also staff can be deleted from the guest list while retaining the staff's
shared person record. Reviews require a checked-out booking, matching the
original application's stated workflow.

## Tests

The non-database checks run with:

```sh
python3 -m unittest discover -s tests -v
```

To include the MySQL integration checks, point to a local secrets file for a
MySQL account that can create databases:

```sh
HMS_TEST_SECRETS_FILE=".streamlit/secrets.toml" python3 -m unittest discover -s tests -v
```

The tests create and remove uniquely named `hms_codex_test_*` databases. They do
not operate on the hotel database named in the original secrets file. Without
`HMS_TEST_SECRETS_FILE`, integration tests are explicitly skipped.
