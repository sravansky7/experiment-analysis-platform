import pandas as pd
from scipy.stats import chisquare

from src.config import RAW_DATA_DIR, OUTPUT_DIR, create_directories


def validate_randomization():
    create_directories()

    assignments = pd.read_csv(
        RAW_DATA_DIR / "assignments.csv"
    )

    variants = pd.read_csv(
        RAW_DATA_DIR / "variants.csv"
    )

    assignments = assignments.merge(
        variants[["variant_id", "variant_name", "allocation"]],
        on="variant_id",
        validate="many_to_one",
    )

    results = []

    for experiment_id, group in assignments.groupby("experiment_id"):
        observed = (
            group["variant_name"]
            .value_counts()
            .reindex(["Control", "Treatment"], fill_value=0)
        )

        allocations = (
            group[["variant_name", "allocation"]]
            .drop_duplicates()
            .set_index("variant_name")["allocation"]
            .reindex(["Control", "Treatment"])
        )

        expected = len(group) * allocations.to_numpy()

        statistic, p_value = chisquare(
            f_obs=observed.to_numpy(),
            f_exp=expected,
        )

        results.append({
            "experiment_id": experiment_id,
            "control_assigned": int(observed["Control"]),
            "treatment_assigned": int(observed["Treatment"]),
            "expected_control": round(expected[0], 2),
            "expected_treatment": round(expected[1], 2),
            "chi_square_statistic": statistic,
            "p_value": p_value,
            "srm_detected": bool(p_value < 0.001),
        })

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        OUTPUT_DIR / "randomization_results.csv",
        index=False,
    )

    print("\n===== RANDOMIZATION VALIDATION =====")
    print(results_df.to_string(index=False))
    print("\nSaved: outputs/randomization_results.csv")

    return results_df


if __name__ == "__main__":
    validate_randomization()