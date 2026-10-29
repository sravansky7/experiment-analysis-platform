
import json
import sqlite3

import pandas as pd

from src.config import RAW_DATA_DIR, OUTPUT_DIR, create_directories

TABLES = {
    "experiments": "experiments.csv",
    "variants": "variants.csv",
    "audience_members": "audience_members.csv",
    "assignments": "assignments.csv",
    "exposure_events": "exposure_events.csv",
    "conversion_events": "conversion_events.csv",
    "guardrail_events": "guardrail_events.csv",
}


SCHEMA = """
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'running', 'completed', 'paused', 'cancelled')
    ),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    random_seed INTEGER NOT NULL,
    CHECK (start_date <= end_date)
);

CREATE TABLE variants (
    variant_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    variant_name TEXT NOT NULL CHECK (
        variant_name IN ('Control', 'Treatment')
    ),
    allocation REAL NOT NULL CHECK (
        allocation > 0 AND allocation <= 1
    ),
    UNIQUE (experiment_id, variant_name),
    UNIQUE (experiment_id, variant_id),
    FOREIGN KEY (experiment_id)
        REFERENCES experiments(experiment_id)
);

CREATE TABLE audience_members (
    user_id TEXT PRIMARY KEY,
    age INTEGER,
    country TEXT,
    eligible INTEGER NOT NULL CHECK (eligible IN (0, 1))
);

CREATE TABLE assignments (
    assignment_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    UNIQUE (experiment_id, user_id),
    FOREIGN KEY (experiment_id)
        REFERENCES experiments(experiment_id),
    FOREIGN KEY (user_id)
        REFERENCES audience_members(user_id),
    FOREIGN KEY (experiment_id, variant_id)
        REFERENCES variants(experiment_id, variant_id)
);

CREATE TABLE exposure_events (
    exposure_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    exposed_at TEXT NOT NULL,
    FOREIGN KEY (assignment_id)
        REFERENCES assignments(assignment_id),
    FOREIGN KEY (experiment_id, variant_id)
        REFERENCES variants(experiment_id, variant_id)
);

CREATE TABLE conversion_events (
    conversion_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    converted_at TEXT NOT NULL,
    conversion_value REAL NOT NULL CHECK (conversion_value >= 0),
    FOREIGN KEY (assignment_id)
        REFERENCES assignments(assignment_id),
    FOREIGN KEY (experiment_id, variant_id)
        REFERENCES variants(experiment_id, variant_id)
);

CREATE TABLE guardrail_events (
    guardrail_event_id INTEGER PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    variant_name TEXT NOT NULL CHECK (
        variant_name IN ('Control', 'Treatment')
    ),
    assigned_users INTEGER NOT NULL CHECK (assigned_users > 0),
    payment_errors INTEGER NOT NULL CHECK (
        payment_errors >= 0 AND payment_errors <= assigned_users
    ),
    refunds INTEGER NOT NULL CHECK (
        refunds >= 0 AND refunds <= assigned_users
    ),
    UNIQUE (experiment_id, variant_name),
    FOREIGN KEY (experiment_id)
        REFERENCES experiments(experiment_id)
);
"""



def load_datasets():
    """Load the generated CSV datasets."""
    datasets = {}

    for table_name, filename in TABLES.items():
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required dataset not found: {file_path}. "
                "Run the data-generation pipeline first."
            )

        datasets[table_name] = pd.read_csv(file_path)

    # Generate a primary key for each guardrail event.
    guardrail_events = datasets["guardrail_events"].copy()
    guardrail_events.insert(
        0,
        "guardrail_event_id",
        range(1, len(guardrail_events) + 1),
    )
    datasets["guardrail_events"] = guardrail_events

    return datasets




def export_json(datasets):
    """Export each dataset as JSON records."""
    json_dir = OUTPUT_DIR / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    for table_name, dataframe in datasets.items():
        output_path = json_dir / f"{table_name}.json"

        records = json.loads(
            dataframe.to_json(orient="records", date_format="iso")
        )

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)

        print(f"JSON exported: {output_path}")


def export_sql(datasets):
    """Create a constrained SQLite database and load all datasets."""
    database_path = OUTPUT_DIR / "experiment_analysis.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if database_path.exists():
        database_path.unlink()

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA)

        # Insert parent tables before dependent tables.
        insertion_order = [
            "experiments",
            "variants",
            "audience_members",
            "assignments",
            "exposure_events",
            "conversion_events",
            "guardrail_events",
        ]

        for table_name in insertion_order:
            dataframe = datasets[table_name]
            dataframe.to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
            )
            print(f"SQLite table loaded: {table_name}")

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

        if foreign_key_errors:
            raise ValueError(
                f"SQLite foreign-key violations: {foreign_key_errors[:10]}"
            )

    print(f"Constrained SQLite database exported: {database_path}")


def export_sql_seed(datasets):
    """Export SQL schema and data as a seed script."""
    sql_path = OUTPUT_DIR / "seed.sql"

    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA)

        insertion_order = [
            "experiments",
            "variants",
            "audience_members",
            "assignments",
            "exposure_events",
            "conversion_events",
            "guardrail_events",
        ]

        for table_name in insertion_order:
            datasets[table_name].to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
            )

        # SQLite's dump includes CREATE TABLE and INSERT statements.
        statements = list(connection.iterdump())

    with open(sql_path, "w", encoding="utf-8") as file:
        file.write("\n".join(statements) + "\n")

    print(f"SQL seed exported: {sql_path}")


def export_data():
    """Export datasets in CSV, JSON, SQLite, and SQL formats."""
    create_directories()
    datasets = load_datasets()

    print("\n===== DATA EXPORT =====")
    print(f"Datasets loaded: {len(datasets)}")
    print(f"CSV source directory: {RAW_DATA_DIR}")

    export_json(datasets)
    export_sql(datasets)
    export_sql_seed(datasets)

    print("\nExport completed successfully!")
    print(f"JSON directory: {OUTPUT_DIR / 'json'}")
    print(f"SQLite database: {OUTPUT_DIR / 'experiment_analysis.db'}")
    print(f"SQL seed: {OUTPUT_DIR / 'seed.sql'}")


if __name__ == "__main__":
    export_data()

