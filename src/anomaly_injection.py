
import shutil

import pandas as pd

from src.config import (
    PROJECT_ROOT,
    RAW_DATA_DIR,
    GROUND_TRUTH_DIR,
    create_directories,
)

ANOMALY_DIR = PROJECT_ROOT / "data" / "processed" / "anomaly_cases"


def prepare_case(case_name):
    """Create an isolated copy of the original datasets."""
    case_dir = ANOMALY_DIR / case_name

    if case_dir.exists():
        shutil.rmtree(case_dir)

    case_dir.mkdir(parents=True, exist_ok=True)

    for file_path in RAW_DATA_DIR.glob("*.csv"):
        shutil.copy2(file_path, case_dir / file_path.name)

    return case_dir


def inject_multiple_variant_assignment():
    case_dir = prepare_case("multiple_variant_assignment")

    path = case_dir / "assignments.csv"
    assignments = pd.read_csv(path)
    variants = pd.read_csv(case_dir / "variants.csv")

    original = assignments.iloc[0].copy()
    experiment_id = original["experiment_id"]
    current_variant = original["variant_id"]

    alternative = variants[
        (variants["experiment_id"] == experiment_id)
        & (variants["variant_id"] != current_variant)
    ].iloc[0]

    duplicate = original.copy()
    duplicate["assignment_id"] = f"{original['assignment_id']}-ANOM-01"
    duplicate["variant_id"] = alternative["variant_id"]

    assignments = pd.concat(
        [assignments, pd.DataFrame([duplicate])],
        ignore_index=True,
    )
    assignments.to_csv(path, index=False)


def inject_exposure_before_assignment():
    case_dir = prepare_case("exposure_before_assignment")

    path = case_dir / "exposure_events.csv"
    exposures = pd.read_csv(path)

    if not exposures.empty:
        exposures.loc[0, "exposed_at"] = "2025-12-31T09:00:00"

    exposures.to_csv(path, index=False)


def inject_inconsistent_conversion_window():
    case_dir = prepare_case("inconsistent_conversion_window")

    path = case_dir / "conversion_events.csv"
    conversions = pd.read_csv(path)

    if not conversions.empty:
        conversions.loc[0, "converted_at"] = "2026-03-15T10:00:00"

    conversions.to_csv(path, index=False)


def inject_sample_ratio_mismatch():
    case_dir = prepare_case("sample_ratio_mismatch")

    path = case_dir / "assignments.csv"
    assignments = pd.read_csv(path)
    variants = pd.read_csv(case_dir / "variants.csv")

    experiment_id = "EXP-2026-000002"

    experiment_variants = variants[
        variants["experiment_id"] == experiment_id
    ]

    control_id = experiment_variants.loc[
        experiment_variants["variant_name"] == "Control",
        "variant_id",
    ].iloc[0]

    treatment_id = experiment_variants.loc[
        experiment_variants["variant_name"] == "Treatment",
        "variant_id",
    ].iloc[0]

    control_indices = assignments[
        (assignments["experiment_id"] == experiment_id)
        & (assignments["variant_id"] == control_id)
    ].index

    # Move a large portion of control assignments to treatment.
    # This intentionally creates a statistically significant SRM.
    indices_to_change = control_indices[: min(200, len(control_indices))]

    assignments.loc[indices_to_change, "variant_id"] = treatment_id
    assignments.to_csv(path, index=False)




def inject_metric_definition_change():
    case_dir = prepare_case("metric_definition_changed")

    definitions = pd.DataFrame([
        {
            "metric_definition_id": "METRIC-CONV-V1",
            "metric_name": "conversion_rate",
            "numerator": "unique_conversions",
            "denominator": "assigned_users",
            "effective_from": "2026-01-01",
            "version": 1,
        },
        {
            "metric_definition_id": "METRIC-CONV-V2",
            "metric_name": "conversion_rate",
            "numerator": "unique_exposed_conversions",
            "denominator": "exposed_users",
            "effective_from": "2026-02-15",
            "version": 2,
        },
    ])

    output_path = case_dir / "metric_definitions.csv"
    definitions.to_csv(output_path, index=False)

    print(f"Metric definitions written to: {output_path}")
    print(f"Versions created: {len(definitions)}")



def main():
    create_directories()
    ANOMALY_DIR.mkdir(parents=True, exist_ok=True)

    inject_multiple_variant_assignment()
    inject_exposure_before_assignment()
    inject_inc_
