
import sqlite3

from src.config import OUTPUT_DIR


def verify_database():
    database_path = OUTPUT_DIR / "experiment_analysis.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")

        print("\n===== DATABASE VERIFICATION =====")

        # 1. Check table counts.
        tables = [
            "experiments",
            "variants",
            "audience_members",
            "assignments",
            "exposure_events",
            "conversion_events",
            "guardrail_events",
        ]

        for table in tables:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: {count:,} rows")

        # 2. Check foreign-key integrity.
        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

        if foreign_key_errors:
            print("FAIL: Foreign-key violations found.")
            print(foreign_key_errors[:10])
        else:
            print("PASS: No foreign-key violations.")

        # 3. Check primary keys and unique constraints.
        index_errors = []

        for table in tables:
            integrity_errors = connection.execute(
                f"PRAGMA integrity_check;"
            ).fetchall()

            if integrity_errors != [("ok",)]:
                index_errors.append((table, integrity_errors))

        if index_errors:
            print("FAIL: Database integrity check failed.")
            print(index_errors)
        else:
            print("PASS: Database integrity check passed.")

        # 4. Confirm foreign keys are defined.
        for table in tables:
            foreign_keys = connection.execute(
                f"PRAGMA foreign_key_list({table});"
            ).fetchall()

            print(f"{table}: {len(foreign_keys)} foreign-key rule(s)")

    print("\nDatabase verification finished.")


if __name__ == "__main__":
    verify_database()
import sqlite3

from src.config import OUTPUT_DIR

with sqlite3.connect(OUTPUT_DIR / "experiment_analysis.db") as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print("\nDatabase tables:")
    for table in tables:
        print("-", table[0])

