-- TravelOps schema (idempotent)
CREATE TABLE IF NOT EXISTS airport (
  airport_id INT PRIMARY KEY AUTO_INCREMENT,
  iata_code  VARCHAR(8)  NOT NULL UNIQUE,
  name       VARCHAR(120) NOT NULL,
  city       VARCHAR(80)  NOT NULL,
  country    VARCHAR(80)  NOT NULL
);

CREATE TABLE IF NOT EXISTS customer (
  customer_id INT PRIMARY KEY AUTO_INCREMENT,
  email       VARCHAR(160) NOT NULL UNIQUE,
  first_name  VARCHAR(80)  NOT NULL,
  last_name   VARCHAR(80)  NOT NULL,
  marketing_ok TINYINT(1) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS flight (
  flight_id   INT PRIMARY KEY AUTO_INCREMENT,
  flight_no   VARCHAR(16) NOT NULL,
  dep_airport INT NOT NULL,
  arr_airport INT NOT NULL,
  dep_time    DATETIME NOT NULL,
  arr_time    DATETIME NOT NULL,
  UNIQUE KEY uniq_flight_slot (flight_no, dep_time),
  CONSTRAINT fk_flight_dep FOREIGN KEY (dep_airport) REFERENCES airport(airport_id),
  CONSTRAINT fk_flight_arr FOREIGN KEY (arr_airport) REFERENCES airport(airport_id)
);

CREATE TABLE IF NOT EXISTS booking (
  booking_id  INT PRIMARY KEY AUTO_INCREMENT,
  customer_id INT NOT NULL,
  flight_id   INT NOT NULL,
  booked_at   DATETIME NOT NULL,
  status      ENUM('CONFIRMED','PENDING','CANCELLED') NOT NULL,
  base_fare   DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_booking_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
  CONSTRAINT fk_booking_flight   FOREIGN KEY (flight_id)   REFERENCES flight(flight_id)
);

CREATE TABLE IF NOT EXISTS payment (
  payment_id INT PRIMARY KEY AUTO_INCREMENT,
  booking_id INT NOT NULL,
  amount     DECIMAL(10,2) NOT NULL,
  method     ENUM('CARD','PAYPAL','VOUCHER','BANK_TRANSFER') NOT NULL,
  currency   CHAR(3) NOT NULL DEFAULT 'GBP',
  paid_at    DATETIME NOT NULL,
  CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES booking(booking_id)
);
