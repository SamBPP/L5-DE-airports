import os
import pandas as pd
import mysql.connector as mysql

def get_conn():
    return mysql.connect(
        host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        user=os.getenv("MYSQL_USER","app_user"),
        password=os.getenv("MYSQL_PASSWORD","app_password"),
        database=os.getenv("MYSQL_DATABASE","travelops_db"),
        autocommit=True,
    )

def fetch_df(cur, sql, params=None):
    cur.execute(sql, params or ())
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

if __name__ == "__main__":
    with get_conn() as conn:
        with conn.cursor() as cur:
            print("Airports (top 10):")
            print(fetch_df(cur, "SELECT airport_id, iata_code, city, country FROM airport ORDER BY airport_id LIMIT 10"))

            print("\nTop customers by spend:")
            sql = '''
            SELECT c.customer_id, c.email,
                   COALESCE(SUM(p.amount),0) AS total_spend,
                   COUNT(DISTINCT b.booking_id) AS bookings
            FROM customer c
            LEFT JOIN booking b ON b.customer_id = c.customer_id
            LEFT JOIN payment p ON p.booking_id = b.booking_id
            GROUP BY c.customer_id, c.email
            ORDER BY total_spend DESC
            LIMIT 10
            '''
            print(fetch_df(cur, sql))

            print("\nFlights today and next 2 days:")
            sql = '''
            SELECT f.flight_id, f.flight_no, da.iata_code AS dep, aa.iata_code AS arr, f.dep_time, f.arr_time
            FROM flight f
            JOIN airport da ON da.airport_id = f.dep_airport
            JOIN airport aa ON aa.airport_id = f.arr_airport
            WHERE f.dep_time >= NOW() AND f.dep_time < DATE_ADD(NOW(), INTERVAL 2 DAY)
            ORDER BY f.dep_time
            LIMIT 20
            '''
            print(fetch_df(cur, sql))
