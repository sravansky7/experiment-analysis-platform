
import pandas as pd
from scipy.stats import chisquare

from src.config import PROJECT_ROOT, OUTPUT_DIR, create_directories


ANOMALY_DIR = PROJECT_ROOT / "data" / "processed" / "anomaly_cases"


def detect_multiple_assignments(case_dir):
    assignments = pd.read_csv(case_dir / "assignments.csv")

    duplicates = assignments[
        assignments.duplicated(
            subset=["experiment_id", "user_id"],
            keep=False,
        )
    ]

    findings = []

    for (experiment_id, user_id), group in duplicates.groupby(
        ["experiment_id", "user_id"]
    ):
        findings.append({
            "anomaly_type": "multiple_variant_assignment",
            "experiment_id": experiment_id,
            "user_id": user_id,
            "details": (
                f"User has {len(group)} assignments in the same experiment."
            ),
        })

    return findings


def detect_exposure_before_assignment(case_dir):
    exposures = pd.read_csv(case_dir / "exposure_events.csv")
    assignments = pd.read_csv(case_dir / "assignments.csv")

    if exposures.empty:
        return []

    joined = exposures.merge(
        assignments[["assignment_id", "assigned_at"]],
        on="assignment_id",
        how="left",
        validate="many_to_one",
    )

    joined["exposed_at"] = pd.to_datetime(
        joined["exposed_at"], errors="coerce"
    )
    joined["assigned_at"] = pd.to_datetime(
        joined["assigned_at"], errors="coerce"
    )

    invalid = joined[
        joined["assigned_at"].notna()
        & joined["exposed_at"].notna()
        & (joined["exposed_at"] < joined["assigned_at"])
    ]

    return [
        {
            "anomaly_type": "exposure_before_assignment",
            "experiment_id": row.experiment_id,
            "user_id": row.user_id,
            "details": "Exposure occurred before assignment.",
        }
        for row in invalid.itertuples(index=False)
    ]


def detect_invalid_conversion_window(case_dir):
    conversions = pd.read_csv(case_dir / "conversion_events.csv")
    experiments = pd.read_csv(case_dir / "experiments.csv")

    if conversions.empty:
        return []

    joined = conversions.merge(
        experiments[["experiment_id", "start_date", "end_date"]],
        on="experiment_id",
        how="left",
        validate="many_to_one",
    )

    joined["converted_at"] = pd.to_datetime(
        joined["converted_at"], errors="coerce"
    )
    joined["start_date"] = pd.to_datetime(
        joined["start_date"], errors="coerce"
    )
    joined["end_date"] = pd.to_datetime(
        joined["end_date"], errors="coerce"
    )

    # Allow conversions through seven days after the experiment end date.
    deadline = joined["end_date"] + pd.Timedelta(days=7)

    invalid = joined[
        joined["converted_at"].notna()
        & (
            (joined["converted_at"] < joined["start_date"])
            | (joined["converted_at"] > deadline)
        )
    ]

    return [
        {
            "anomaly_type": "inconsistent_conversion_window",
            "experiment_id": row.experiment_id,
            "user_id": row.user_id,
            "details": (
                f"Conversion timestamp {row.converted_at} falls outside "
                "the permitted outcome window."
            ),
        }
        for row in invalid.itertuples(index=False)
    ]



def detect_sample_ratio_mismatch(case_dir):
    assignments = pd.read_csv(case_dir / "assignments.csv")
    variants = pd.read_csv(case_dir / "variants.csv")

    findings = []

    for experiment_id, group in assignments.groupby("experiment_id"):
        experiment_variants = variants[
            variants["experiment_id"] == experiment_id
        ].copy()

        if experiment_variants.empty:
            continue

        counts = (
            group["variant_id"]
            .value_counts()
            .reindex(experiment_variants["variant_id"], fill_value=0)
        )

        allocations = experiment_variants.set_index(
            "variant_id"
        )["allocation"]

        expected = (
            allocations / allocations.sum() * len(group)
        )

        statistic, p_value = chisquare(
            f_obs=counts.to_numpy(),
            f_exp=expected.reindex(counts.index).to_numpy(),
        )

        if p_value < 0.01:
            findings.append({
                "anomaly_type": "sample_ratio_mismatch",
                "experiment_id": experiment_id,
                "user_id": "",
                "details": (
                    f"SRM detected: chi-square={statistic:.3f}, "
                    f"p-value={p_value:.6g}; "
                    f"observed counts={counts.to_dict()}."
                ),
            })

    return findings




def detect_metric_definition_change(case_dir):
    path = case_dir / "metric_definitions.csv"

    if not path.exists():
        return []

    definitions = pd.read_csv(path)

    required_columns = {
        "metric_name",
        "numerator",
        "denominator",
        "effective_from",
        "version",
    }

    if not required_columns.issubset(definitions.columns):
        return [{
            "anomaly_type": "invalid_metric_definition",
            "experiment_id": "",
            "user_id": "",
            "details": "Metric definitions file is missing required columns.",
        }]

    findings = []

    for metric_name, group in definitions.groupby("metric_name"):
        group = group.sort_values("effective_from")

        changed = group[
            ["numerator", "denominator"]
        ].drop_duplicates().shape[0] > 1

        if len(group) > 1 and changed:
            versions = group["version"].astype(str).tolist()

            findings.append({
                "anomaly_type": "metric_definition_changed",
                "experiment_id": "",
                "user_id": "",
                "details": (
                    f"Metric '{metric_name}' has different numerator or "
                    f"denominator definitions across versions {versions}. "
                    "Review the effective dates and existing results."
                ),
            })

    return findings


def detect_case(case_name):
    case_dir = ANOMALY_DIR / case_name

    if not case_dir.exists():
        print(f"Warning: Missing anomaly case: {case_name}")
        return []

    detectors = [
        detect_multiple_assignments,
        detect_exposure_before_assignment,
        detect_invalid_conversion_window,
        detect_sample_ratio_mismatch,
        detect_metric_definition_change,
    ]

    findings = []

    for detector in detectors:
        findings.extend(detector(case_dir))

    for finding in findings:
        finding["case_name"] = case_name

    return findings


def main():
    create_directories()

    case_names = [
        "multiple_variant_assignment",
        "exposure_before_assignment",
        "inconsistent_conversion_window",
        "sample_ratio_mismatch",
        "metric_definition_changed",
    ]

    findings = []

    for case_name in case_names:
        findings.extend(detect_case(case_name))

    columns = [
        "case_name",
        "anomaly_type",
        "experiment_id",
        "user_id",
        "details",
    ]

    report = pd.DataFrame(findings, columns=columns)
    report_path = OUTPUT_DIR / "anomaly_detection_report.csv"
    report.to_csv(report_path, index=False)

    print("\n===== ANOMALY DETECTION SUMMARY =====")
    print(f"Anomaly findings: {len(report)}")

    if not report.empty:
        print(
            report.groupby(["case_name", "anomaly_type"])
            .size()
            .to_string()
        )

    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
