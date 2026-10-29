
import pandas as pd

from src.config import RAW_DATA_DIR


def validate_data():
    experiments = pd.read_csv(RAW_DATA_DIR / "experiments.csv")
    variants = pd.read_csv(RAW_DATA_DIR / "variants.csv")
    audience = pd.read_csv(RAW_DATA_DIR / "audience_members.csv")
    assignments = pd.read_csv(RAW_DATA_DIR / "assignments.csv")
    exposures = pd.read_csv(RAW_DATA_DIR / "exposure_events.csv")
    conversions = pd.read_csv(RAW_DATA_DIR / "conversion_events.csv")

    errors = []

    # 1. Required columns
    required_columns = {
        "experiments": (experiments, [
            "experiment_id", "status", "start_date", "end_date"
        ]),
        "variants": (variants, [
            "variant_id", "experiment_id", "variant_name", "allocation"
        ]),
        "audience": (audience, [
            "user_id", "eligible"
        ]),
        "assignments": (assignments, [
            "assignment_id", "experiment_id", "user_id",
            "variant_id", "assigned_at"
        ]),
        "exposures": (exposures, [
            "exposure_id", "experiment_id", "assignment_id",
            "user_id", "variant_id", "exposed_at"
        ]),
        "conversions": (conversions, [
            "conversion_id", "experiment_id", "assignment_id",
            "user_id", "variant_id", "converted_at",
            "conversion_value"
        ]),
    }

    for table_name, (df, columns) in required_columns.items():
        missing = set(columns) - set(df.columns)
        if missing:
            errors.append(
                f"{table_name}: missing columns {sorted(missing)}"
            )

    # Stop safely if required columns are missing.
    if errors:
        print("\n===== DATA VALIDATION REPORT =====")
        print(f"FAILED: {len(errors)} validation issue(s)")
        for error in errors:
            print(f"- {error}")
        return errors

    # 2. Required values and primary-key uniqueness
    primary_keys = [
        (experiments, "experiment_id"),
        (variants, "variant_id"),
        (audience, "user_id"),
        (assignments, "assignment_id"),
        (exposures, "exposure_id"),
        (conversions, "conversion_id"),
    ]

    for df, column in primary_keys:
        if df[column].isna().any() or df[column].astype(str).str.strip().eq("").any():
            errors.append(f"{column}: missing primary keys")

        if df[column].duplicated().any():
            errors.append(f"{column}: duplicate primary keys")

    # 3. Valid experiment lifecycle and status
    valid_statuses = {"draft", "running", "completed", "paused", "cancelled"}

    if not experiments["status"].isin(valid_statuses).all():
        errors.append("Experiments contain invalid status values")

    start_dates = pd.to_datetime(experiments["start_date"], errors="coerce")
    end_dates = pd.to_datetime(experiments["end_date"], errors="coerce")

    if start_dates.isna().any() or end_dates.isna().any():
        errors.append("Experiments contain invalid start or end dates")
    elif (start_dates > end_dates).any():
        errors.append("Experiment start date occurs after end date")

    # 4. Allocation and enum validation
    if variants["variant_name"].isna().any():
        errors.append("Variant names cannot be missing")

    if not variants["variant_name"].isin({"Control", "Treatment"}).all():
        errors.append("Variants contain invalid variant names")

    allocations = pd.to_numeric(variants["allocation"], errors="coerce")

    if allocations.isna().any() or ((allocations <= 0) | (allocations > 1)).any():
        errors.append("Variant allocations must be greater than 0 and at most 1")

    allocation_sums = variants.assign(
        _allocation=allocations
    ).groupby("experiment_id")["_allocation"].sum()

    if not allocation_sums.between(0.999999, 1.000001).all():
        errors.append("Variant allocations must sum to 1 per experiment")

    if audience["eligible"].isna().any():
        errors.append("Audience eligibility values cannot be missing")

    eligible_values = audience["eligible"].astype(str).str.lower()
    if not eligible_values.isin({"true", "false"}).all():
        errors.append("Audience eligibility must contain only true/false values")

    # 5. Foreign-key integrity
    experiment_ids = set(experiments["experiment_id"])
    variant_ids = set(variants["variant_id"])
    user_ids = set(audience["user_id"])
    assignment_ids = set(assignments["assignment_id"])

    if not variants["experiment_id"].isin(experiment_ids).all():
        errors.append("Variants reference unknown experiments")

    if not assignments["experiment_id"].isin(experiment_ids).all():
        errors.append("Assignments reference unknown experiments")

    if not assignments["variant_id"].isin(variant_ids).all():
        errors.append("Assignments reference unknown variants")

    if not assignments["user_id"].isin(user_ids).all():
        errors.append("Assignments reference unknown users")

    for name, df in [
        ("Exposure", exposures),
        ("Conversion", conversions),
    ]:
        if not df["assignment_id"].isin(assignment_ids).all():
            errors.append(f"{name} events reference unknown assignments")

        if not df["variant_id"].isin(variant_ids).all():
            errors.append(f"{name} events reference unknown variants")

        if not df["experiment_id"].isin(experiment_ids).all():
            errors.append(f"{name} events reference unknown experiments")

    # 6. Assignment consistency
    variant_experiment = variants.set_index("variant_id")["experiment_id"]
    variant_lookup = variants.set_index("variant_id")["variant_name"]

    assignment_lookup = assignments.set_index("assignment_id")

    if assignments["variant_id"].isin(variant_ids).all():
        expected_experiment = assignments["variant_id"].map(variant_experiment)
        if not expected_experiment.equals(assignments["experiment_id"]):
            errors.append("Assignment experiment does not match its variant")

    if assignments["variant_id"].isin(variant_ids).all():
        control_treatment = assignments["variant_id"].map(variant_lookup)
        if control_treatment.isna().any():
            errors.append("Assignments reference variants without names")

    if assignments["user_id"].isin(user_ids).all():
        eligible_lookup = audience.set_index("user_id")["eligible"]
        assigned_eligibility = assignments["user_id"].map(eligible_lookup)

        eligible_bool = assigned_eligibility.astype(str).str.lower().eq("true")
        if not eligible_bool.all():
            errors.append("Ineligible users have assignments")

    # A user may have only one variant per experiment.
    assignment_counts = assignments.groupby(
        ["experiment_id", "user_id"]
    )["variant_id"].nunique()

    if (assignment_counts > 1).any():
        errors.append("Users assigned to multiple variants")

    if assignments.duplicated(["experiment_id", "user_id"]).any():
        errors.append("Duplicate user assignments within an experiment")

    # 7. Event-to-assignment consistency and timestamps
    assignment_columns = [
        "experiment_id", "user_id", "variant_id", "assigned_at"
    ]

    assignment_reference = assignments[
        ["assignment_id"] + assignment_columns
    ].drop_duplicates("assignment_id").set_index("assignment_id")

    for name, df, event_time_column in [
        ("Exposure", exposures, "exposed_at"),
        ("Conversion", conversions, "converted_at"),
    ]:
        if df.empty:
            continue

        known_assignments = df["assignment_id"].isin(assignment_reference.index)
        if not known_assignments.all():
            continue

        for column in ["experiment_id", "user_id", "variant_id"]:
            expected = df["assignment_id"].map(assignment_reference[column])
            if not expected.equals(df[column]):
                errors.append(
                    f"{name} event {column} does not match its assignment"
                )

        event_times = pd.to_datetime(df[event_time_column], errors="coerce")
        assigned_times = pd.to_datetime(
            df["assignment_id"].map(assignment_reference["assigned_at"]),
            errors="coerce",
        )

        if event_times.isna().any():
            errors.append(f"{name} events contain invalid timestamps")
        elif assigned_times.isna().any():
            errors.append("Assignments contain invalid timestamps")
        elif (event_times < assigned_times).any():
            errors.append(f"{name} event occurs before assignment")
    
    # 7B. Validate conversion events against the experiment window
    experiment_dates = experiments.set_index("experiment_id")[
        ["start_date", "end_date"]
    ].copy()

    experiment_dates["start_date"] = pd.to_datetime(
        experiment_dates["start_date"], errors="coerce"
    )
    experiment_dates["end_date"] = pd.to_datetime(
        experiment_dates["end_date"], errors="coerce"
    )

    if not conversions.empty:
        conversion_times = pd.to_datetime(
            conversions["converted_at"], errors="coerce"
        )

        conversion_starts = conversions["experiment_id"].map(
            experiment_dates["start_date"]
        )
        conversion_ends = conversions["experiment_id"].map(
            experiment_dates["end_date"]
        )

        valid_dates = (
            conversion_times.notna()
            & conversion_starts.notna()
            & conversion_ends.notna()
        )

        if not valid_dates.all():
            errors.append(
                "Conversion events contain invalid timestamps or experiment dates"
            )
        else:
            outside_window = (
                (conversion_times < conversion_starts)
                | (conversion_times.dt.normalize() > conversion_ends.dt.normalize())
            )

            if outside_window.any():
                errors.append(
                    "Conversion events occur outside their experiment window"
                )



    # 8. Conversion value validation
    conversion_values = pd.to_numeric(
        conversions["conversion_value"], errors="coerce"
    )

    if conversion_values.isna().any():
        errors.append("Conversion values must be numeric and non-missing")
    elif (conversion_values < 0).any():
        errors.append("Conversion values cannot be negative")

    # 9. Report
    print("\n===== DATA VALIDATION REPORT =====")

    if errors:
        print(f"FAILED: {len(errors)} validation issue(s)")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASSED: All implemented validation checks.")

    print("\nRecord counts:")
    print(f"Experiments: {len(experiments)}")
    print(f"Variants: {len(variants)}")
    print(f"Audience members: {len(audience)}")
    print(f"Assignments: {len(assignments)}")
    print(f"Exposure events: {len(exposures)}")
    print(f"Conversion events: {len(conversions)}")

    return errors


if __name__ == "__main__":
    validate_data()

