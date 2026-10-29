import numpy as np
import pandas as pd

from src.config import (
    RANDOM_SEED,
    RAW_DATA_DIR,
    create_directories,
)


def generate_events():
    rng = np.random.default_rng(RANDOM_SEED)

    assignments = pd.read_csv(RAW_DATA_DIR / "assignments.csv")
    audience = pd.read_csv(RAW_DATA_DIR / "audience_members.csv")
    variants = pd.read_csv(RAW_DATA_DIR / "variants.csv")

    assignments = assignments.merge(
        variants[["variant_id", "variant_name"]],
        on="variant_id",
        validate="many_to_one",
    )

    assignments = assignments.merge(
        audience[["user_id", "eligible"]],
        on="user_id",
        validate="many_to_one",
    )

    exposure_events = []
    conversion_events = []

    exposure_counter = 1
    conversion_counter = 1

    for row in assignments.itertuples(index=False):
        # Simulate whether the assigned user sees the variant.
        exposed = rng.random() < 0.90

        if exposed:
            exposure_events.append({
                "exposure_id": f"EXPOS-{exposure_counter:06d}",
                "experiment_id": row.experiment_id,
                "assignment_id": row.assignment_id,
                "user_id": row.user_id,
                "variant_id": row.variant_id,
                "exposed_at": "2026-01-02T10:00:00",
            })
            exposure_counter += 1

        # Simulate conversion using assignment, not ground truth.
        base_rate = 0.10
        treatment_effect = 0.02 if row.variant_name == "Treatment" else 0.0

        converted = rng.random() < (base_rate + treatment_effect)

        if converted:
            conversion_events.append({
                "conversion_id": f"CONV-2026-{conversion_counter:06d}",
                "experiment_id": row.experiment_id,
                "assignment_id": row.assignment_id,
                "user_id": row.user_id,
                "variant_id": row.variant_id,
                "converted_at": "2026-01-05T10:00:00",
                "conversion_value": round(
                    float(rng.uniform(100, 2000)), 2
                ),
            })
            conversion_counter += 1

    pd.DataFrame(exposure_events).to_csv(
        RAW_DATA_DIR / "exposure_events.csv", index=False
    )

    pd.DataFrame(conversion_events).to_csv(
        RAW_DATA_DIR / "conversion_events.csv", index=False
    )

    print("Event generation completed!")
    print(f"Exposure events: {len(exposure_events)}")
    print(f"Conversion events: {len(conversion_events)}")


if __name__ == "__main__":
    create_directories()
    generate_events()