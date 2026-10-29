import numpy as np
import pandas as pd

from src.config import RANDOM_SEED, RAW_DATA_DIR, OUTPUT_DIR, create_directories


def calculate_guardrails():
    create_directories()

    rng = np.random.default_rng(RANDOM_SEED)

    assignments = pd.read_csv(
        RAW_DATA_DIR / "assignments.csv"
    )

    variants = pd.read_csv(
        RAW_DATA_DIR / "variants.csv"
    )

    assignments = assignments.merge(
        variants[["variant_id", "variant_name"]],
        on="variant_id",
        validate="many_to_one",
    )

    results = []

    for experiment_id, group in assignments.groupby("experiment_id"):

        for variant_name, variant_group in group.groupby("variant_name"):

            n = len(variant_group)

            # Simulated guardrail outcomes.
            # Experiment 5 deliberately has elevated treatment error rates.
            error_probability = 0.02

            if (
                experiment_id == "EXP-2026-000005"
                and variant_name == "Treatment"
            ):
                error_probability = 0.08

            payment_errors = int(
                rng.binomial(n, error_probability)
            )

            refund_probability = 0.03

            refunds = int(
                rng.binomial(n, refund_probability)
            )

            results.append({
                "experiment_id": experiment_id,
                "variant_name": variant_name,
                "assigned_users": n,
                "payment_errors": payment_errors,
                "payment_error_rate": payment_errors / n,
                "refunds": refunds,
                "refund_rate": refunds / n,
            })

    metrics = pd.DataFrame(results)

    comparisons = []

    for experiment_id, group in metrics.groupby("experiment_id"):

        control = group[group["variant_name"] == "Control"]
        treatment = group[group["variant_name"] == "Treatment"]

        if control.empty or treatment.empty:
            continue

        c = control.iloc[0]
        t = treatment.iloc[0]

        error_difference = (
            t["payment_error_rate"] - c["payment_error_rate"]
        )

        refund_difference = (
            t["refund_rate"] - c["refund_rate"]
        )

        # Flag when the treatment error rate is at least
        # 3 percentage points higher than control.
        error_regression = error_difference >= 0.03

        # Flag when the treatment refund rate is at least
        # 2 percentage points higher than control.
        refund_regression = refund_difference >= 0.02

        comparisons.append({
            "experiment_id": experiment_id,
            "control_error_rate": c["payment_error_rate"],
            "treatment_error_rate": t["payment_error_rate"],
            "error_rate_difference": error_difference,
            "error_guardrail_failed": error_regression,
            "control_refund_rate": c["refund_rate"],
            "treatment_refund_rate": t["refund_rate"],
            "refund_rate_difference": refund_difference,
            "refund_guardrail_failed": refund_regression,
            "overall_guardrail_status": (
                "FAIL"
                if error_regression or refund_regression
                else "PASS"
            ),
        })

    comparison_df = pd.DataFrame(comparisons)

    metrics.to_csv(
        OUTPUT_DIR / "guardrail_metrics.csv",
        index=False,
    )

    comparison_df.to_csv(
        OUTPUT_DIR / "guardrail_results.csv",
        index=False,
    )

    print("\n===== GUARDRAIL ANALYSIS =====")
    print(comparison_df.to_string(index=False))

    print("\nSaved:")
    print(OUTPUT_DIR / "guardrail_metrics.csv")
    print(OUTPUT_DIR / "guardrail_results.csv")

    return comparison_df


if __name__ == "__main__":
    calculate_guardrails()