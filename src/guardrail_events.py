
import numpy as np
import pandas as pd

from src.config import RANDOM_SEED, RAW_DATA_DIR, create_directories


def generate_guardrail_events():
    """Generate reproducible synthetic payment-error and refund outcomes."""
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

    for (experiment_id, variant_name), group in assignments.groupby(
        ["experiment_id", "variant_name"],
        sort=True,
    ):
        user_count = len(group)

        # Default synthetic payment-error probability.
        error_probability = 0.02

        # Deliberately introduce a guardrail regression in experiment 5.
        if (
            experiment_id == "EXP-2026-000005"
            and variant_name == "Treatment"
        ):
            error_probability = 0.08

        payment_errors = rng.binomial(
            user_count,
            error_probability,
        )

        refund_probability = 0.03

        refunds = rng.binomial(
            user_count,
            refund_probability,
        )

        results.append({
            "experiment_id": experiment_id,
            "variant_name": variant_name,
            "assigned_users": user_count,
            "payment_errors": int(payment_errors),
            "refunds": int(refunds),
        })

    dataframe = pd.DataFrame(results)

    output_path = RAW_DATA_DIR / "guardrail_events.csv"

    dataframe.to_csv(output_path, index=False)

    print("Guardrail source data generated successfully.")
    print(f"Records: {len(dataframe)}")
    print(f"Saved: {output_path}")

    return dataframe


if __name__ == "__main__":
    generate_guardrail_events()
