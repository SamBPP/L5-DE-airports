# TravelOps: MySQL + Python in GitHub Codespaces

Spin up a Codespace with MySQL 8 and Python ready to seed a realistic travel dataset and run example queries.

## Quick Start
1. **Create Codespace** on this repo (Code → Create Codespace on main).
2. **Wait for build**: dependencies from `app/requirements.txt` install automatically.
3. **Verify MySQL connectivity** (optional CLI inside Codespace):
   ```bash
   mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT VERSION();"
   ```
4. **Seed data** using your provided script (connection details are read from environment variables):
   ```bash
   python app/seed_airports_mysql.py --reset --customers 300 --airports 25 --days 30 --partial-payments
   ```
   Re-run without `--reset` to add more data later.
5. **Run example queries**:
   ```bash
   python app/query_examples.py
   ```

## How it works
- MySQL service is defined in `docker-compose.yml` and seeded with `app/schema.sql` on first start.
- Environment vars are provided by `.devcontainer/devcontainer.json` so your scripts don't need to hardcode connection settings.
- Your original `seed_airports_mysql.py` drives all data generation.

## Resetting the DB
- Stop the Codespace (or Dev Container), then remove the `mysql-data` volume locally if needed.
- Or run with `--reset` flag to truncate tables in FK-safe order.

## Notes
- Tables: `airport`, `customer`, `flight`, `booking`, `payment` (see `app/schema.sql`).

