
import pandas as pd

from src.config import RAW_DATA_DIR, OUTPUT_DIR, create_directories


ERROR_REGRESSION_THRESHOLD = 0.03
REFUND_REGRESSION_THRESHOLD = 0.02


def calculate_guardrails():
    """Evaluate guardrails using previously generated source data."""
    create_directories()

    source_path = RAW_DATA_DIR / "guardrail_events.csv"

    if not source_path.exists():
        raise FileNotFoundError(
            f"Guardrail source data not found: {source_path}. "
            "Run 'python -m src.guardrail_events' first."
        )

    metrics = pd.read_csv(source_path)

    required_columns = {
        "experiment_id",
        "variant_name",
        "assigned_users",
        "payment_errors",
        "refunds",
    }

    missing_columns = required_columns - set(metrics.columns)

    if missing_columns:
        raise ValueError(
            f"Guardrail dataset is missing columns: {sorted(missing_columns)}"
        )

    if metrics.duplicated(["experiment_id", "variant_name"]).any():
        raise ValueError(
            "Duplicate experiment/variant records found in guardrail data."
        )

    if not metrics["variant_name"].isin(["Control", "Treatment"]).all():
        raise ValueError("Unknown variant name in guardrail data.")

    if (metrics["assigned_users"] <= 0).any():
        raise ValueError("assigned_users must be greater than zero.")

    for column in ["payment_errors", "refunds"]:
        if (metrics[column] < 0).any():
            raise ValueError(f"{column} cannot be negative.")

        if (metrics[column] > metrics["assigned_users"]).any():
            raise ValueError(
                f"{column} cannot exceed assigned_users."
            )

    metrics["payment_error_rate"] = (
        metrics["payment_errors"] / metrics["assigned_users"]
    )

    metrics["refund_rate"] = (
        metrics["refunds"] / metrics["assigned_users"]
    )

    comparisons = []

    for experiment_id, group in metrics.groupby("experiment_id"):
        control = group[group["variant_name"] == "Control"]
        treatment = group[group["variant_name"] == "Treatment"]

        if len(control) != 1 or len(treatment) != 1:
            raise ValueError(
                f"{experiment_id} must have exactly one Control "
                "and one Treatment guardrail record."
            )

        c = control.iloc[0]
        t = treatment.iloc[0]

        error_difference = (
            t["payment_error_rate"] - c["payment_error_rate"]
        )

        refund_difference = (
            t["refund_rate"] - c["refund_rate"]
        )

        error_regression = (
            error_difference >= ERROR_REGRESSION_THRESHOLD
        )

        refund_regression = (
            refund_difference >= REFUND_REGRESSION_THRESHOLD
        )

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
