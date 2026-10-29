import numpy as np
import pandas as pd
from scipy.stats import norm

from src.config import RAW_DATA_DIR, OUTPUT_DIR, create_directories


def calculate_metrics():
    create_directories()

    assignments = pd.read_csv(
        RAW_DATA_DIR / "assignments.csv"
    )
    variants = pd.read_csv(
        RAW_DATA_DIR / "variants.csv"
    )
    conversions = pd.read_csv(
        RAW_DATA_DIR / "conversion_events.csv"
    )

    # Attach variant names to assignments.
    assignments = assignments.merge(
        variants[["variant_id", "variant_name"]],
        on="variant_id",
        validate="many_to_one",
    )

    # Count conversions using experiment and assignment IDs.
    # Never attribute a conversion using user_id alone.
    converted_assignments = conversions[
        ["experiment_id", "assignment_id"]
    ].drop_duplicates()

    converted_assignments["converted"] = 1

    assignments = assignments.merge(
        converted_assignments,
        on=["experiment_id", "assignment_id"],
        how="left",
        validate="one_to_one",
    )

    assignments["converted"] = (
        assignments["converted"].fillna(0).astype(int)
    )

    # Calculate variant-level metrics.
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

    results["conversion_rate"] = (
        results["conversions"] / results["assigned_users"]
    )

    results.to_csv(
        OUTPUT_DIR / "variant_metrics.csv",
        index=False,
    )

    # Estimate treatment effects.
    comparisons = []

    for experiment_id, group in results.groupby("experiment_id"):
        control = group[group["variant_name"] == "Control"]
        treatment = group[group["variant_name"] == "Treatment"]

        if control.empty or treatment.empty:
            continue

        c = control.iloc[0]
        t = treatment.iloc[0]

        p_control = c["conversion_rate"]
        p_treatment = t["conversion_rate"]

        absolute_effect = p_treatment - p_control

        relative_effect = (
            absolute_effect / p_control
            if p_control > 0
            else np.nan
        )

        n_control = int(c["assigned_users"])
        n_treatment = int(t["assigned_users"])

        standard_error = np.sqrt(
            p_control * (1 - p_control) / n_control
            + p_treatment * (1 - p_treatment) / n_treatment
        )

        if standard_error > 0:
            z_score = absolute_effect / standard_error
            p_value = 2 * norm.sf(abs(z_score))

            ci_lower = absolute_effect - 1.96 * standard_error
            ci_upper = absolute_effect + 1.96 * standard_error
        else:
            p_value = np.nan
            ci_lower = np.nan
            ci_upper = np.nan

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
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
            "p_value": p_value,
            "statistically_significant": (
                bool(p_value < 0.05)
                if pd.notna(p_value)
                else False
            ),
        })

    comparison_df = pd.DataFrame(comparisons)

    comparison_df.to_csv(
        OUTPUT_DIR / "experiment_results.csv",
        index=False,
    )

    print("\n===== EXPERIMENT ANALYSIS =====")

    if not comparison_df.empty:
        print(
            comparison_df.to_string(index=False)
        )

    print("\nResults saved:")
    print(OUTPUT_DIR / "variant_metrics.csv")
    print(OUTPUT_DIR / "experiment_results.csv")

    return comparison_df


if __name__ == "__main__":
    calculate_metrics()