from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

RANDOM_SEED = 20261022

STARTER_USERS = 1000
FULL_USERS = 50000
NUM_EXPERIMENTS = 10


DATASET_MODE = "full"  
def get_user_count():
    if DATASET_MODE == "full":
        return FULL_USERS
    return STARTER_USERS
CONTROL_ALLOCATION = 0.50
TREATMENT_ALLOCATION = 0.50


SIGNIFICANCE_LEVEL = 0.05
CONFIDENCE_LEVEL = 0.95


def create_directories():
    directories = [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        GROUND_TRUTH_DIR,
        OUTPUT_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    create_directories()
    print("Project configuration initialized successfully!")