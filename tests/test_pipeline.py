
import pandas as pd

from src.data_generator import (
    generate_experiments,
    generate_variants,
    generate_audience,
    generate_assignments,
)
from src.validation import validate_data
from src.anomaly_detector import detect_case


def test_generate_experiments():
    experiments = generate_experiments()

    assert len(experiments) == 10
    assert experiments["experiment_id"].is_unique


def test_generate_variants():
    experiments = generate_experiments()
    variants = generate_variants(experiments)

    assert len(variants) == 20
    assert variants["variant_id"].is_unique


def test_generate_audience():
    audience = generate_audience()

    assert len(audience) > 0
    assert audience["user_id"].is_unique
    assert audience["eligible"].notna().all()


def test_generate_assignments():
    experiments = generate_experiments()
    variants = generate_variants(experiments)
    audience = generate_audience()
    assignments = generate_assignments(experiments, audience, variants)

    assert not assignments.empty
    assert assignments["assignment_id"].is_unique
    assert assignments["user_id"].isin(audience["user_id"]).all()


def test_anomaly_detector_finds_multiple_assignments():
    findings = detect_case("multiple_variant_assignment")

    assert any(
        finding["anomaly_type"] == "multiple_variant_assignment"
        for finding in findings
    )


def test_anomaly_detector_finds_exposure_before_assignment():
    findings = detect_case("exposure_before_assignment")

    assert any(
        finding["anomaly_type"] == "exposure_before_assignment"
        for finding in findings
    )


def test_anomaly_detector_finds_invalid_conversion_window():
    findings = detect_case("inconsistent_conversion_window")

    assert any(
        finding["anomaly_type"] == "inconsistent_conversion_window"
        for finding in findings
    )


def test_anomaly_detector_finds_metric_definition_change():
    findings = detect_case("metric_definition_changed")

    assert any(
        finding["anomaly_type"] == "metric_definition_changed"
        for finding in findings
    )



def test_validation_detects_conversion_outside_experiment_window(
    tmp_path, monkeypatch
):
    import pandas as pd
    from src import validation

    # Create a minimal, internally consistent dataset.
    experiments = pd.DataFrame([{
        "experiment_id": "EXP-TEST",
        "status": "completed",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
    }])

    variants = pd.DataFrame([{
        "variant_id": "VAR-TEST-A",
        "experiment_id": "EXP-TEST",
        "variant_name": "Control",
        "allocation": 0.5,
    }, {
        "variant_id": "VAR-TEST-B",
        "experiment_id": "EXP-TEST",
        "variant_name": "Treatment",
        "allocation": 0.5,
    }])

    audience = pd.DataFrame([{
        "user_id": "USR-TEST",
        "eligible": True,
    }])

    assignments = pd.DataFrame([{
        "assignment_id": "ASG-TEST",
        "experiment_id": "EXP-TEST",
        "user_id": "USR-TEST",
        "variant_id": "VAR-TEST-A",
        "assigned_at": "2026-01-01T10:00:00",
    }])

    exposures = pd.DataFrame(columns=[
        "exposure_id", "experiment_id", "assignment_id",
        "user_id", "variant_id", "exposed_at",
    ])

    conversions = pd.DataFrame([{
        "conversion_id": "CONV-TEST",
        "experiment_id": "EXP-TEST",
        "assignment_id": "ASG-TEST",
        "user_id": "USR-TEST",
        "variant_id": "VAR-TEST-A",
        "converted_at": "2026-02-15T10:00:00",
        "conversion_value": 100.0,
    }])

    tables = {
        "experiments.csv": experiments,
        "variants.csv": variants,
        "audience_members.csv": audience,
        "assignments.csv": assignments,
        "exposure_events.csv": exposures,
        "conversion_events.csv": conversions,
    }

    for filename, dataframe in tables.items():
        dataframe.to_csv(tmp_path / filename, index=False)

    monkeypatch.setattr(validation, "RAW_DATA_DIR", tmp_path)

    errors = validation.validate_data()

    assert any(
        "outside their experiment window" in error
        for error in errors
    )

