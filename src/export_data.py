
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
}


def load_datasets():
    """Load generated CSV datasets."""
    datasets = {}

    for table_name, filename in TABLES.items():
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required dataset not found: {file_path}. "
                "Run the data-generation pipeline first."
            )

        datasets[table_name] = pd.read_csv(file_path)

    return datasets


def export_json(datasets):
    """Export each dataset as a JSON file."""
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
    """Create a SQLite database containing all exported tables."""
    database_path = OUTPUT_DIR / "experiment_analysis.db"

    if database_path.exists():
        database_path.unlink()

    with sqlite3.connect(database_path) as connection:
        for table_name, dataframe in datasets.items():
            dataframe.to_sql(
                table_name,
                connection,
                if_exists="replace",
                index=False,
            )

    print(f"SQLite database exported: {database_path}")


def export_sql_seed(datasets):
    """Export SQL CREATE TABLE and INSERT statements."""
    sql_path = OUTPUT_DIR / "seed.sql"

    with sqlite3.connect(":memory:") as connection:
        for table_name, dataframe in datasets.items():
            dataframe.to_sql(
                table_name,
                connection,
                if_exists="replace",
                index=False,
            )

        statements = [
            "PRAGMA foreign_keys = ON;",
            "",
        ]

        # Export schema and data using SQLite's SQL dump.
        statements.extend(connection.iterdump())

    with open(sql_path, "w", encoding="utf-8") as file:
        file.write("\n".join(statements))

    print(f"SQL seed exported: {sql_path}")


def export_data():
    """Export datasets in CSV, JSON and SQL-compatible formats."""
    create_directories()

    datasets = load_datasets()

    print("\n===== DATA EXPORT =====")
    print(f"Datasets loaded: {len(datasets)}")

    # CSV files already exist in data/raw/.
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
