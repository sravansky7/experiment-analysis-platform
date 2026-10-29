
import numpy as np
import pandas as pd

from src.config import (
    RANDOM_SEED,
    NUM_EXPERIMENTS,
    RAW_DATA_DIR,
    create_directories,
    get_user_count,
    DATASET_MODE,
)


def generate_experiments():
    """Generate experiment master records."""
    experiments = []

    for i in range(1, NUM_EXPERIMENTS + 1):
        experiments.append({
            "experiment_id": f"EXP-2026-{i:06d}",
            "experiment_name": f"Checkout Experiment {i}",
            "hypothesis": "The treatment variant improves purchase conversion.",
            "primary_metric": "conversion_rate",
            "status": "completed",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "random_seed": RANDOM_SEED + i,
        })

    return pd.DataFrame(experiments)


def generate_variants(experiments):
    """Generate control and treatment variants."""
    variants = []

    for experiment_id in experiments["experiment_id"]:
        variants.extend([
            {
                "variant_id": f"VAR-{experiment_id}-A",
                "experiment_id": experiment_id,
                "variant_name": "Control",
                "allocation": 0.50,
            },
            {
                "variant_id": f"VAR-{experiment_id}-B",
                "experiment_id": experiment_id,
                "variant_name": "Treatment",
                "allocation": 0.50,
            },
        ])

    return pd.DataFrame(variants)


def generate_audience():
    """Generate the requested number of eligible users."""
    rng = np.random.default_rng(RANDOM_SEED)
    user_count = get_user_count()

    # Full mode produces exactly 50,000 eligible users.
    # Starter mode produces a smaller development dataset.
    if DATASET_MODE == "full":
        eligible = np.ones(user_count, dtype=bool)
    else:
        eligible = rng.choice(
            [True, False],
            size=user_count,
            p=[0.95, 0.05],
        )

    return pd.DataFrame({
        "user_id": [
            f"USR-{i:06d}"
            for i in range(1, user_count + 1)
        ],
        "age": rng.integers(18, 66, size=user_count),
        "country": rng.choice(
            ["India", "USA", "UK", "Canada"],
            size=user_count,
        ),
        "eligible": eligible,
    })


def generate_assignments(experiments, audience, variants):
    """Randomly assign eligible users within each experiment."""
    rng = np.random.default_rng(RANDOM_SEED)
    assignments = []

    eligible_users = audience.loc[
        audience["eligible"], "user_id"
    ]

    for experiment_id in experiments["experiment_id"]:
        experiment_variants = variants[
            variants["experiment_id"] == experiment_id
        ]

        variant_ids = experiment_variants["variant_id"].to_numpy()

        for user_id in eligible_users:
            variant_id = rng.choice(variant_ids)

            assignments.append({
                "assignment_id": f"ASG-{experiment_id}-{user_id}",
                "experiment_id": experiment_id,
                "user_id": user_id,
                "variant_id": variant_id,
                "assigned_at": "2026-01-01T10:00:00",
            })

    return pd.DataFrame(assignments)


def main():
    create_directories()

    experiments = generate_experiments()
    variants = generate_variants(experiments)
    audience = generate_audience()
    assignments = generate_assignments(
        experiments, audience, variants
    )

    experiments.to_csv(RAW_DATA_DIR / "experiments.csv", index=False)
    variants.to_csv(RAW_DATA_DIR / "variants.csv", index=False)
    audience.to_csv(RAW_DATA_DIR / "audience_members.csv", index=False)
    assignments.to_csv(RAW_DATA_DIR / "assignments.csv", index=False)

    print("\nSynthetic data generated successfully!")
    print(f"Dataset mode: {DATASET_MODE}")
    print(f"Experiments: {len(experiments)}")
    print(f"Variants: {len(variants)}")
    print(f"Audience members: {len(audience)}")
    print(f"Eligible users: {int(audience['eligible'].sum())}")
    print(f"Assignments: {len(assignments)}")


if __name__ == "__main__":
    main()

