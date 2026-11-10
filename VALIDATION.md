# Validation — November 10, 2026

## Automated checks

The 23-test baseline passed, including real MySQL integration tests in isolated
temporary databases. The suite covered all ten operational pages, the complete hotel →
room → guest → booking → payment → review flow, and the database copy command.

Additional checks covered duplicate emails/reviews, invalid dates and amounts,
missing records, escaped review text, paginated searches, shared staff identity
preservation, verified cloud TLS settings, local TOML compatibility, sign-in,
CSRF, production setup requirements, and temporary CA-file cleanup.

Booking checks covered overlapping and adjacent dates, room/hotel mismatches,
reopening cancelled reservations, and two simultaneous requests for the same
room. Partial guest creation and failed room assignments rolled back correctly.

The data-copy test preserved IDs and staff relationships in a second temporary
database, verified row counts, and refused to overwrite a populated target.

The suite now includes 24 cases. Targeted checks of the expanded dashboard and
all ten pages against an empty database passed after adding the existing GitHub
dashboard's occupancy, room availability, status charts, and paid revenue. The
dashboard check verifies that pending payments and older months are excluded
from the six-month chart while the paid total includes all paid records.

## Browser checks

Chrome loaded the application over a local HTTP server using synthetic records
in a temporary database. Desktop (1440 px) and phone (390 px) screenshots were
inspected. The ten operational pages had no horizontal page overflow or
duplicate HTML element IDs at phone width. The booking room selector correctly
filtered its options when the selected hotel changed.

## Deployment still required

The user created a TiDB Cloud Starter instance and provided a SQL Editor result
showing that the corrected schema script completed successfully. The TiDB-only
CHECK constraint setting uses SET GLOBAL, as required by TiDB. Hosted driver
TLS, cloud record copying, and a Vercel build remain to be verified. Local tests
used Python 3.14; Vercel is configured for Python 3.12.

The original Desktop project and its hotel database were not modified. Only
uniquely named test databases were created and removed. No original credentials
or guest records are included in the package.
