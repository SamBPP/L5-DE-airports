#!/usr/bin/env python3
"""
Seed the airports MySQL schema with synthetic data.
(See comments inside for usage and options.)
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

try:
    import mysql.connector as mysql
except Exception as e:
    print("ERROR: mysql-connector-python not installed. Install with: pip install mysql-connector-python", file=sys.stderr)
    raise

try:
    from faker import Faker  # type: ignore
    _FAKER_AVAILABLE = True
except Exception:
    _FAKER_AVAILABLE = False
    Faker = None  # type: ignore

AIRPORT_POOL: List[Tuple[str, str, str]] = [
    ("LHR","Heathrow","London,UK"),
    ("LGW","Gatwick","London,UK"),
    ("MAN","Manchester","Manchester,UK"),
    ("EDI","Edinburgh","Edinburgh,UK"),
    ("JFK","John F. Kennedy","New York,USA"),
    ("EWR","Newark Liberty","Newark,USA"),
    ("LAX","Los Angeles Intl","Los Angeles,USA"),
    ("SFO","San Francisco Intl","San Francisco,USA"),
    ("SEA","Seattle-Tacoma","Seattle,USA"),
    ("ORD","O'Hare","Chicago,USA"),
    ("DFW","Dallas/Fort Worth","Dallas,USA"),
    ("YYZ","Pearson","Toronto,CAN"),
    ("YVR","Vancouver Intl","Vancouver,CAN"),
    ("CDG","Charles de Gaulle","Paris,FRA"),
    ("ORY","Orly","Paris,FRA"),
    ("AMS","Schiphol","Amsterdam,NLD"),
    ("FRA","Frankfurt","Frankfurt,DEU"),
    ("MUC","Munich","Munich,DEU"),
    ("MAD","Barajas","Madrid,ESP"),
    ("BCN","El Prat","Barcelona,ESP"),
    ("DXB","Dubai Intl","Dubai,ARE"),
    ("HKG","Hong Kong Intl","Hong Kong,CHN"),
    ("SIN","Changi","Singapore,SGP"),
    ("NRT","Narita","Tokyo,JPN"),
    ("HND","Haneda","Tokyo,JPN"),
    ("SYD","Kingsford Smith","Sydney,AUS"),
    ("MEL","Tullamarine","Melbourne,AUS"),
    ("DOH","Hamad Intl","Doha,QAT"),
    ("ICN","Incheon","Seoul,KOR"),
    ("ZRH","Zurich","Zurich,CHE"),
]

FIRST_NAMES = ["Ava","Liam","Noah","Olivia","Emma","Sophia","Mason","Isabella","Mia","Lucas","Ethan","Amelia","Harper","Ella","Aria","Leo","James","Henry","Freya","Isla"]
LAST_NAMES  = ["Singh","Jones","Patel","Smith","Brown","Wilson","Taylor","Davies","Evans","Thomas","Johnson","Williams","Martin","Thompson","White","Walker","Harris","Lewis","Clarke","Hall"]
EMAIL_DOMAINS = ["example.com","mail.com","gmail.com","outlook.com","yahoo.com"]
PAY_METHODS = ["CARD","PAYPAL","VOUCHER","BANK_TRANSFER"]

def parse_args():
    """Parse CLI arguments using environment variables as defaults."""

    p = argparse.ArgumentParser(description="Seed TravelOps MySQL data")
    p.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    p.add_argument("--user", default=os.getenv("MYSQL_USER"))
    p.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    p.add_argument("--database", default=os.getenv("MYSQL_DATABASE"))
    p.add_argument("--reset", action="store_true", help="Truncate tables before seeding (FK-safe order)")
    p.add_argument("--airports", type=int, default=20, help="Target number of airports")
    p.add_argument("--customers", type=int, default=300, help="Target number of customers")
    p.add_argument("--days", type=int, default=30, help="Window of days for flights (past and future combined)")
    p.add_argument("--flights-per-day", type=int, default=None, help="Approx flights per day; default scales with airports")
    p.add_argument("--bookings-per-customer", type=float, default=1.0, help="Average bookings per customer")
    p.add_argument("--confirmed-rate", type=float, default=0.7)
    p.add_argument("--pending-rate", type=float, default=0.2)
    p.add_argument("--cancelled-rate", type=float, default=0.1)
    p.add_argument("--partial-payments", action="store_true", help="Allow partial prepayments for PENDING bookings")
    p.add_argument("--currency", default="GBP", help="Currency code for payments (3 letters)")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = p.parse_args()

    # Ensure required connection details are present either via args or env vars
    missing = [name for name in ("user", "password", "database") if getattr(args, name) is None]
    if missing:
        p.error(
            "--user/--password/--database required (or set MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)"
        )

    return args

def connect(args):
    conn = mysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password, database=args.database,
        autocommit=False
    )
    return conn

def get_count(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])

def truncate_all(conn):
    print("Truncating tables (FK-safe order)...")
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for t in ["payment","booking","flight","customer","airport"]:
            try:
                cur.execute(f"TRUNCATE TABLE {t}")
            except Exception as e:
                print(f"  skip TRUNCATE {t}: {e}")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()

def ensure_airports(conn, target_airports: int):
    from random import randint
    with conn.cursor() as cur:
        existing = get_count(cur, "airport")
        to_add = max(0, target_airports - existing)
        if to_add == 0:
            print(f"Airports OK: {existing} exist (target {target_airports})")
            return
        print(f"Inserting {to_add} airports (existing {existing}, target {target_airports})...")

        pool = []
        for code, name, city_country in AIRPORT_POOL:
            if "," in city_country:
                city, country = city_country.split(",", 1)
            else:
                city, country = city_country, ""
            pool.append((code, name, city, country))

        i = 0
        while len(pool) < target_airports:
            code = f"A{(i//100)%10}{(i//10)%10}{i%10}"
            pool.append((code, f"Synth {code}", f"City{code}", "ZZ"))
            i += 1

        cur.execute("SELECT iata_code FROM airport")
        have = {row[0] for row in cur.fetchall()}

        inserted = 0
        for code, name, city, country in pool:
            if inserted >= to_add:
                break
            if code in have:
                continue
            cur.execute(
                "INSERT INTO airport (iata_code, name, city, country) VALUES (%s,%s,%s,%s)",
                (code, name, city, country)
            )
            inserted += 1
        conn.commit()
        print(f"Inserted airports: {inserted}")

def generate_name_email(fake: Optional['Faker'], idx: int) -> Tuple[str,str,str]:
    if fake:
        first = fake.first_name()
        last  = fake.last_name()
        email = fake.unique.email()
        return first, last, email.lower()
    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    email = f"{first}.{last}.{idx}@{random.choice(EMAIL_DOMAINS)}".lower()
    return first, last, email

def ensure_customers(conn, target_customers: int, seed: int):
    fake = Faker() if _FAKER_AVAILABLE else None
    if fake:
        fake.seed_instance(seed)
    with conn.cursor() as cur:
        existing = get_count(cur, "customer")
        to_add = max(0, target_customers - existing)
        if to_add == 0:
            print(f"Customers OK: {existing} exist (target {target_customers})")
            return
        print(f"Inserting {to_add} customers (existing {existing}, target {target_customers})...")
        inserted = 0
        start_idx = existing + 1
        for i in range(to_add):
            first, last, email = generate_name_email(fake, start_idx + i)
            marketing_ok = 1 if random.random() < 0.35 else 0
            cur.execute(
                "INSERT INTO customer (email, first_name, last_name, marketing_ok) VALUES (%s,%s,%s,%s)",
                (email, first, last, marketing_ok)
            )
            inserted += 1
        conn.commit()
        print(f"Inserted customers: {inserted}")

def ensure_flights(conn, days: int, flights_per_day: Optional[int]):
    now = datetime.now()
    start = now - timedelta(days=days//2)

    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT airport_id FROM airport")
        airports = cur.fetchall()
        if len(airports) < 2:
            raise RuntimeError("Need at least 2 airports to generate flights")
        airport_ids = [a["airport_id"] for a in airports]

        if flights_per_day is None:
            flights_per_day = max(10, len(airport_ids) // 2)

        target_flights = flights_per_day * days

        existing = get_count(cur, "flight")
        to_add = max(0, target_flights - existing)
        if to_add == 0:
            print(f"Flights OK: {existing} exist (target ~{target_flights})")
            return
        print(f"Inserting ~{to_add} flights over {days} days (~{flights_per_day}/day)...")

        pairs = [(dep, arr) for dep in airport_ids for arr in airport_ids if dep != arr]

        inserted = 0
        for d in range(days):
            day = start + timedelta(days=d)
            for _ in range(flights_per_day):
                dep_id, arr_id = random.choice(pairs)
                dep_time = day.replace(hour=5, minute=0, second=0, microsecond=0) + timedelta(minutes=random.randint(0, 18*60))
                duration_min = random.randint(90, 12*60)
                arr_time = dep_time + timedelta(minutes=duration_min)
                flight_no = f"TO{random.randint(100,999)}"
                try:
                    cur.execute(
                        "INSERT INTO flight (flight_no, dep_airport, arr_airport, dep_time, arr_time) VALUES (%s,%s,%s,%s,%s)",
                        (flight_no, dep_id, arr_id, dep_time, arr_time)
                    )
                    inserted += 1
                except Exception:
                    # Skip rare collisions
                    pass
            conn.commit()
        print(f"Inserted flights: {inserted}")

def ensure_bookings_and_payments(conn, bookings_per_customer: float, rates: Tuple[float,float,float], partial_payments: bool, currency: str):
    confirmed_rate, pending_rate, cancelled_rate = rates
    if abs((confirmed_rate + pending_rate + cancelled_rate) - 1.0) > 1e-6:
        raise ValueError("Rates must sum to 1.0")

    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT customer_id FROM customer"); customer_ids = [r["customer_id"] for r in cur.fetchall()]
        cur.execute("SELECT flight_id, dep_time FROM flight"); flights_rows = cur.fetchall()

        if not customer_ids or not flights_rows:
            raise RuntimeError("Need customers and flights before creating bookings")

        target_bookings = int(len(customer_ids) * bookings_per_customer)
        existing = get_count(cur, "booking")
        to_add = max(0, target_bookings - existing)
        if to_add == 0:
            print(f"Bookings OK: {existing} exist (target ~{target_bookings})")
            return
        print(f"Inserting ~{to_add} bookings (avg {bookings_per_customer:.2f} per customer)...")

        inserted_b = 0
        inserted_p = 0

        for i in range(to_add):
            cust_id = random.choice(customer_ids)
            fl      = random.choice(flights_rows)
            flight_id = fl["flight_id"]
            dep_time  = fl["dep_time"]
            booked_at = dep_time - timedelta(days=random.randint(1, 60), minutes=random.randint(0, 59))

            r = random.random()
            if r < confirmed_rate:
                status = "CONFIRMED"
            elif r < confirmed_rate + pending_rate:
                status = "PENDING"
            else:
                status = "CANCELLED"

            base_fare = round(random.uniform(60, 250) if random.random() < 0.6 else random.uniform(250, 900), 2)

            cur.execute(
                "INSERT INTO booking (customer_id, flight_id, booked_at, status, base_fare) VALUES (%s,%s,%s,%s,%s)",
                (cust_id, flight_id, booked_at, status, base_fare)
            )
            booking_id = cur.lastrowid
            inserted_b += 1

            if status == "CONFIRMED":
                amount = base_fare
                cur.execute(
                    "INSERT INTO payment (booking_id, amount, method, currency, paid_at) VALUES (%s,%s,%s,%s,%s)",
                    (booking_id, amount, random.choice(PAY_METHODS), currency, booked_at + timedelta(minutes=random.randint(1, 1440)))
                )
                inserted_p += 1
            elif status == "PENDING" and partial_payments and random.random() < 0.3:
                amount = round(base_fare * random.uniform(0.1, 0.4), 2)
                if amount == 0:
                    amount = 1.00
                cur.execute(
                    "INSERT INTO payment (booking_id, amount, method, currency, paid_at) VALUES (%s,%s,%s,%s,%s)",
                    (booking_id, amount, random.choice(PAY_METHODS), currency, booked_at + timedelta(minutes=random.randint(1, 1440)))
                )
                inserted_p += 1

            if i % 1000 == 0:
                conn.commit()

        conn.commit()
        print(f"Inserted bookings: {inserted_b}, payments: {inserted_p}")

def main():
    args = parse_args()
    random.seed(args.seed)
    conn = connect(args)
    try:
        if args.reset:
            truncate_all(conn)
        ensure_airports(conn, args.airports)
        ensure_customers(conn, args.customers, args.seed)
        flights_per_day = args.flights_per_day
        if flights_per_day is None:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM airport")
                flights_per_day = max(10, int(cur.fetchone()[0]) // 2)
        ensure_flights(conn, args.days, flights_per_day)
        ensure_bookings_and_payments(
            conn,
            bookings_per_customer=args.bookings_per_customer,
            rates=(args.confirmed_rate, args.pending_rate, args.cancelled_rate),
            partial_payments=args.partial_payments,
            currency=args.currency
        )
        with conn.cursor() as cur:
            print("\\nFinal counts:")
            for t in ["airport","customer","flight","booking","payment"]:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                print(f"  {t:8s}: {cur.fetchone()[0]}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
