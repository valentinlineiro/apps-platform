"""
Seed aneca_journal_index from journals.csv (exported from Supabase autoaneca project).

Usage (local SQLite):
    python seed_journals.py journals.csv

Usage (running stack — seeds the shared Postgres):
    docker compose exec aneca-advisor-backend python seed_journals.py /app/journals.csv

CSV columns: issn_1, issn_2, quartile, title, h_index, category
"""
import csv
import os
import sqlite3
import sys


def main(csv_path: str) -> None:
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        try:
            import psycopg2
        except ImportError:
            print("psycopg2 not installed — run: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        placeholder = "%s"
    else:
        db_path = os.environ.get("REGISTRY_DB_PATH", "/tmp/aneca_registry.sqlite3")
        conn = sqlite3.connect(db_path)
        placeholder = "?"

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r.get("issn_1"), r.get("issn_2"), r["quartile"], r.get("title"),
                int(r["h_index"]) if r.get("h_index") else None, r.get("category"),
            )
            for r in reader
        ]

    cur = conn.cursor()
    cur.execute("DELETE FROM aneca_journal_index")
    cur.executemany(
        f"INSERT INTO aneca_journal_index (issn_1, issn_2, quartile, title, h_index, category)"
        f" VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} journal records.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python seed_journals.py <journals.csv>")
        sys.exit(1)
    main(sys.argv[1])
