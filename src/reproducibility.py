
import hashlib
import subprocess
import sys

from src.config import RAW_DATA_DIR
from src.guardrail_events import generate_guardrail_events


FILES_TO_CHECK = [
    "experiments.csv",
    "variants.csv",
    "audience_members.csv",
    "assignments.csv",
    "exposure_events.csv",
    "conversion_events.csv",
    "guardrail_events.csv",
]


def calculate_checksums():
    """Calculate SHA-256 checksums for generated datasets."""
    checksums = {}

    for filename in FILES_TO_CHECK:
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing dataset: {file_path}"
            )

        with open(file_path, "rb") as file:
            checksums[filename] = hashlib.sha256(
                file.read()
            ).hexdigest()

    return checksums


def verify_reproducibility():
    """Run generation twice and compare output checksums."""
    print("REPRODUCIBILITY CHECK")
    print("=" * 50)

    print("\nRun 1: Generating datasets...")
    subprocess.run(
        [sys.executable, "-m", "src.data_generator"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "src.events"],
        check=True,
    )
    generate_guardrail_events()
    first_run = calculate_checksums()

    print("\nRun 2: Regenerating datasets...")
    subprocess.run(
        [sys.executable, "-m", "src.data_generator"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "src.events"],
        check=True,
    )
    generate_guardrail_events()
    second_run = calculate_checksums()

    print("\nCHECKSUM COMPARISON")
    print("-" * 50)

    all_match = True

    for filename in FILES_TO_CHECK:
        matches = first_run[filename] == second_run[filename]
        print(f"{filename}: {'MATCH' if matches else 'MISMATCH'}")

        if not matches:
            all_match = False

    print("\nRESULT:")
    if all_match:
        print("PASS: All generated datasets are reproducible.")
    else:
        print("FAIL: Some generated datasets differ.")

    return all_match


if __name__ == "__main__":
    success = verify_reproducibility()
    sys.exit(0 if success else 1)
