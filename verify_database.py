import sqlite3

database_path = "outputs/experiment_analysis.db"

with sqlite3.connect(database_path) as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' ORDER BY name"
    ).fetchall()

    assignment_count = connection.execute(
        "SELECT COUNT(*) FROM assignments"
    ).fetchone()[0]

    print("Tables:", tables)
    print("Number of tables:", len(tables))
    print("Assignment rows:", assignment_count)

    assert len(tables) == 6, "Expected 6 tables"
    assert assignment_count == 500_000, "Expected 500,000 assignments"

    print("PASS: Database verification successful.")