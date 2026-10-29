
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.config import (
    RAW_DATA_DIR,
    OUTPUT_DIR,
    SIGNIFICANCE_LEVEL,
    CONFIDENCE_LEVEL,
    create_directories,
)


def holm_adjust(p_values):
    """Apply Holm's step-down correction to a collection of p-values."""
    p_values = np.asarray(p_values, dtype=float)
    adjusted = np.full(len(p_values), np.nan)

    valid_indices = np.flatnonzero(np.isfinite(p_values))

    if len(valid_indices) == 0:
        return adjusted

    valid_p = p_values[valid_indices]
    order = np.argsort(valid_p)
    sorted_p = valid_p[order]
    number_of_tests = len(sorted_p)

    sorted_adjusted = np.maximum.accumulate(
        (number_of_tests - np.arange(number_of_tests)) * sorted_p
    )
    sorted_adjusted = np.clip(sorted_adjusted, 0, 1)

    adjusted[valid_indices[order]] = sorted_adjusted

    return adjusted


def calculate_metrics():
    """Calculate intention-to-treat conversion effects by experiment."""
    create_directories()

    assignments = pd.read_csv(RAW_DATA_DIR / "assignments.csv")
    variants = pd.read_csv(RAW_DATA_DIR / "variants.csv")
    conversions = pd.read_csv(
        RAW_DATA_DIR / "conversion_events.csv"
    )

    required_assignment_columns = {
        "assignment_id",
        "experiment_id",
        "user_id",
        "variant_id",
    }
    required_variant_columns = {
        "variant_id",
        "experiment_id",
        "variant_name",
    }
    required_conversion_columns = {
        "conversion_id",
        "experiment_id",
        "assignment_id",
    }

    if not required_assignment_columns.issubset(assignments.columns):
        raise ValueError("Assignments dataset is missing required columns.")

    if not required_variant_columns.issubset(variants.columns):
        raise ValueError("Variants dataset is missing required columns.")

    if not required_conversion_columns.issubset(conversions.columns):
        raise ValueError("Conversions dataset is missing required columns.")

    if assignments["assignment_id"].duplicated().any():
        raise ValueError("Duplicate assignment_id values detected.")

    if assignments.duplicated(
        ["experiment_id", "user_id"]
    ).any():
        raise ValueError(
            "A user has multiple assignments in the same experiment."
        )

    if variants["variant_id"].duplicated().any():
        raise ValueError("Duplicate variant_id values detected.")

    # Validate that every assignment references an existing variant
    # belonging to the same experiment.
    assignment_variants = assignments.merge(
        variants[["variant_id", "experiment_id", "variant_name"]],
        on=["variant_id", "experiment_id"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    if (assignment_variants["_merge"] != "both").any():
        raise ValueError(
            "Assignments contain unknown variants or mismatched experiments."
        )

    # Validate conversion references before deduplicating conversions.
    valid_assignments = assignments[
        ["assignment_id", "experiment_id"]
    ].drop_duplicates()

    conversion_check = conversions.merge(
        valid_assignments,
        on=["assignment_id", "experiment_id"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    if (conversion_check["_merge"] != "both").any():
        raise ValueError(
            "Conversion events contain invalid assignment references."
        )

    # A binary conversion outcome counts each assigned user at most once
    # per experiment, even if duplicate conversion events exist.
    converted_assignments = conversions[
        ["experiment_id", "assignment_id"]
    ].drop_duplicates()

    converted_assignments["converted"] = 1

    assignments = assignment_variants.drop(columns="_merge").merge(
        converted_assignments,
        on=["experiment_id", "assignment_id"],
        how="left",
        validate="one_to_one",
    )

    assignments["converted"] = (
        assignments["converted"].fillna(0).astype(int)
    )

    results = (
        assignments.groupby(
            ["experiment_id", "variant_id", "variant_name"]
        )
        .agg(
            assigned_users=("user_id", "nunique"),
            conversions=("converted", "sum"),
        )
        .reset_index()
    )

    if (results["assigned_users"] <= 0).any():
        raise ValueError("An analyzed variant has no assigned users.")

    results["conversion_rate"] = (
        results["conversions"] / results["assigned_users"]
    )

    results.to_csv(OUTPUT_DIR / "variant_metrics.csv", index=False)

    # Calculate the normal-approximation confidence interval.
    alpha = 1 - CONFIDENCE_LEVEL
    z_critical = norm.ppf(1 - alpha / 2)

    comparisons = []

    for experiment_id, group in results.groupby("experiment_id"):
        control = group[group["variant_name"] == "Control"]
        treatment = group[group["variant_name"] == "Treatment"]

        if len(control) != 1 or len(treatment) != 1:
            raise ValueError(
                f"{experiment_id} must have exactly one Control "
                "and one Treatment variant."
            )

        c = control.iloc[0]
        t = treatment.iloc[0]

        p_control = float(c["conversion_rate"])
        p_treatment = float(t["conversion_rate"])

        absolute_effect = p_treatment - p_control

        relative_effect = (
            absolute_effect / p_control
            if p_control > 0
            else np.nan
        )

        n_control = int(c["assigned_users"])
        n_treatment = int(t["assigned_users"])

        standard_error = float(np.sqrt(
            p_control * (1 - p_control) / n_control
            + p_treatment * (1 - p_treatment) / n_treatment
        ))

        if standard_error > 0:
            z_score = absolute_effect / standard_error
            p_value = float(2 * norm.sf(abs(z_score)))

            ci_lower = absolute_effect - z_critical * standard_error
            ci_upper = absolute_effect + z_critical * standard_error
        else:
            p_value = 1.0 if absolute_effect == 0 else np.nan
            ci_lower = absolute_effect
            ci_upper = absolute_effect

        comparisons.append({
            "experiment_id": experiment_id,
            "control_users": n_control,
            "treatment_users": n_treatment,
            "control_conversions": int(c["conversions"]),
            "treatment_conversions": int(t["conversions"]),
            "control_conversion_rate": p_control,
            "treatment_conversion_rate": p_treatment,
            "absolute_effect": absolute_effect,
            "relative_effect": relative_effect,
            "confidence_level": CONFIDENCE_LEVEL,
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
            "standard_error": standard_error,
            "p_value": p_value,
        })

    comparison_df = pd.DataFrame(comparisons)

    if not comparison_df.empty:
        comparison_df["holm_adjusted_p_value"] = holm_adjust(
            comparison_df["p_value"].to_numpy()
        )

        comparison_df["statistically_significant"] = (
            comparison_df["p_value"] < SIGNIFICANCE_LEVEL
        )

        comparison_df["significant_after_holm"] = (
            comparison_df["holm_adjusted_p_value"] < SIGNIFICANCE_LEVEL
        )

    comparison_df.to_csv(
        OUTPUT_DIR / "experiment_results.csv",
        index=False,
    )

    print("\n===== EXPERIMENT ANALYSIS =====")

    if not comparison_df.empty:
        print(comparison_df.to_string(index=False))

    print("\nResults saved:")
    print(OUTPUT_DIR / "variant_metrics.csv")
    print(OUTPUT_DIR / "experiment_results.csv")

    return comparison_df


if __name__ == "__main__":
    calculate_metrics()

