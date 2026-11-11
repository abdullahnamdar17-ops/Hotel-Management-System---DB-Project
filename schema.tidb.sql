-- TiDB Cloud Starter setup: run this entire script together in a new, empty database.
CREATE DATABASE IF NOT EXISTS hotel_management_system;
USE hotel_management_system;
SET GLOBAL tidb_enable_check_constraint = ON;

-- Run once in a NEW, empty MySQL 8+ database selected by your provider.
-- This creates the original application tables without dropping existing tables.

CREATE TABLE hotels (
    hotel_id        INT AUTO_INCREMENT,
    hotel_name      VARCHAR(100) NOT NULL,
    contact_phone   VARCHAR(20)  NOT NULL,
    street_address  VARCHAR(150) NOT NULL,
    city            VARCHAR(80)  NOT NULL,
    state_province  VARCHAR(80)  NOT NULL,
    zip_code        VARCHAR(20)  NOT NULL,
    star_rating     DECIMAL(2,1),

    CONSTRAINT pk_hotels
        PRIMARY KEY (hotel_id),

    CONSTRAINT ck_hotels_star_rating
        CHECK (star_rating BETWEEN 1.0 AND 5.0)
);


-- =====================================================
-- PERSONS (shared details for guests and staff)
-- =====================================================

CREATE TABLE persons (
    person_id       INT AUTO_INCREMENT,
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NOT NULL,
    email           VARCHAR(100) NOT NULL,
    phone           VARCHAR(20)  NOT NULL,
    age             INT          NOT NULL,
    street_address  VARCHAR(150) NOT NULL,
    city            VARCHAR(80)  NOT NULL,
    state_province  VARCHAR(80)  NOT NULL,
    zip_code        VARCHAR(20)  NOT NULL,

    CONSTRAINT pk_persons
        PRIMARY KEY (person_id),

    CONSTRAINT uk_persons_email
        UNIQUE (email),

    CONSTRAINT ck_persons_age
        CHECK (age >= 18)
);


-- =====================================================
-- GUESTS (subtype of persons)
-- =====================================================

CREATE TABLE guests (
    guest_id        INT         NOT NULL,
    guest_status    VARCHAR(30) NOT NULL DEFAULT 'active',
    loyalty_level   VARCHAR(30) NOT NULL DEFAULT 'none',

    CONSTRAINT pk_guests
        PRIMARY KEY (guest_id),

    CONSTRAINT fk_guests_persons
        FOREIGN KEY (guest_id)
        REFERENCES persons (person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- =====================================================
-- STAFF ROLES
-- =====================================================

CREATE TABLE staff_roles (
    staff_role_id  INT AUTO_INCREMENT,
    role_name      VARCHAR(50) NOT NULL,

    CONSTRAINT pk_staff_roles
        PRIMARY KEY (staff_role_id),

    CONSTRAINT uk_staff_roles_role_name
        UNIQUE (role_name)
);


-- =====================================================
-- STAFF
-- =====================================================

CREATE TABLE staff (
    staff_id        INT          NOT NULL,
    hotel_id        INT          NOT NULL,
    staff_role_id   INT          NOT NULL,
    salary          DECIMAL(10,2) NOT NULL,

    CONSTRAINT pk_staff
        PRIMARY KEY (staff_id),

    CONSTRAINT fk_staff_persons
        FOREIGN KEY (staff_id)
        REFERENCES persons (person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_staff_hotels
        FOREIGN KEY (hotel_id)
        REFERENCES hotels (hotel_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_staff_roles
        FOREIGN KEY (staff_role_id)
        REFERENCES staff_roles (staff_role_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT ck_staff_salary
        CHECK (salary > 0)
);


-- =====================================================
-- ROOM TYPES
-- =====================================================

CREATE TABLE room_types (
    room_type_id  INT AUTO_INCREMENT,
    type_name     VARCHAR(50)   NOT NULL,
    capacity      INT           NOT NULL,
    base_price    DECIMAL(10,2) NOT NULL,

    CONSTRAINT pk_room_types
        PRIMARY KEY (room_type_id),

    CONSTRAINT uk_room_types_type_name
        UNIQUE (type_name),

    CONSTRAINT ck_room_types_capacity
        CHECK (capacity >= 1),

    CONSTRAINT ck_room_types_base_price
        CHECK (base_price > 0)
);


-- =====================================================
-- ROOMS
-- =====================================================

CREATE TABLE rooms (
    room_id       INT AUTO_INCREMENT,
    hotel_id      INT         NOT NULL,
    room_type_id  INT         NOT NULL,
    room_number   VARCHAR(20) NOT NULL,
    room_status   VARCHAR(30) NOT NULL DEFAULT 'available',

    CONSTRAINT pk_rooms
        PRIMARY KEY (room_id),

    CONSTRAINT uk_rooms_hotel_room_number
        UNIQUE (hotel_id, room_number),

    CONSTRAINT fk_rooms_hotels
        FOREIGN KEY (hotel_id)
        REFERENCES hotels (hotel_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_rooms_room_types
        FOREIGN KEY (room_type_id)
        REFERENCES room_types (room_type_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);


-- =====================================================
-- BOOKINGS
-- =====================================================

CREATE TABLE bookings (
    booking_id       INT AUTO_INCREMENT,
    guest_id         INT  NOT NULL,
    hotel_id         INT  NOT NULL,
    booking_date     DATE NOT NULL,
    check_in_date    DATE NOT NULL,
    check_out_date   DATE NOT NULL,
    booking_status   VARCHAR(30) NOT NULL DEFAULT 'reserved',

    CONSTRAINT pk_bookings
        PRIMARY KEY (booking_id),

    CONSTRAINT fk_bookings_guests
        FOREIGN KEY (guest_id)
        REFERENCES guests (guest_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_bookings_hotels
        FOREIGN KEY (hotel_id)
        REFERENCES hotels (hotel_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT ck_bookings_dates
        CHECK (check_out_date > check_in_date),

    CONSTRAINT ck_bookings_booking_date
        CHECK (booking_date <= check_in_date)
);


-- =====================================================
-- BOOKING_ROOMS
-- =====================================================

CREATE TABLE booking_rooms (
    booking_id           INT NOT NULL,
    room_id              INT NOT NULL,
    agreed_nightly_rate  DECIMAL(10,2) NOT NULL,

    CONSTRAINT pk_booking_rooms
        PRIMARY KEY (booking_id, room_id),

    CONSTRAINT fk_booking_rooms_bookings
        FOREIGN KEY (booking_id)
        REFERENCES bookings (booking_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_booking_rooms_rooms
        FOREIGN KEY (room_id)
        REFERENCES rooms (room_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT ck_booking_rooms_rate
        CHECK (agreed_nightly_rate > 0)
);


-- =====================================================
-- PAYMENTS
-- =====================================================

CREATE TABLE payments (
    payment_id      INT AUTO_INCREMENT,
    booking_id      INT NOT NULL,
    payment_date    DATE NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    payment_method  VARCHAR(30) NOT NULL,
    payment_status  VARCHAR(30) NOT NULL DEFAULT 'paid',

    CONSTRAINT pk_payments
        PRIMARY KEY (payment_id),

    CONSTRAINT fk_payments_bookings
        FOREIGN KEY (booking_id)
        REFERENCES bookings (booking_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT ck_payments_amount
        CHECK (amount > 0)
);


-- =====================================================
-- REVIEWS
-- =====================================================

CREATE TABLE reviews (
    review_id    INT AUTO_INCREMENT,
    booking_id   INT NOT NULL,
    rating       INT NOT NULL,
    review_text  TEXT,
    review_date  DATE NOT NULL,

    CONSTRAINT pk_reviews
        PRIMARY KEY (review_id),

    CONSTRAINT uk_reviews_booking
        UNIQUE (booking_id),

    CONSTRAINT fk_reviews_bookings
        FOREIGN KEY (booking_id)
        REFERENCES bookings (booking_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT ck_reviews_rating
        CHECK (rating BETWEEN 1 AND 5)
);


-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX idx_bookings_check_in_date
    ON bookings (check_in_date);

CREATE INDEX idx_bookings_check_out_date
    ON bookings (check_out_date);

CREATE INDEX idx_rooms_room_status
    ON rooms (room_status);

CREATE INDEX idx_payments_payment_date
    ON payments (payment_date);

CREATE INDEX idx_payments_payment_status
    ON payments (payment_status);
