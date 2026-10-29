from src.config import create_directories
from src.data_generator import main as generate_master_data
from src.events import generate_events
from src.validation import validate_data
from src.randomization import validate_randomization
from src.metrics import calculate_metrics
from src.guardrails import calculate_guardrails


def run_pipeline():
    print("=" * 60)
    print("EXPERIMENT ANALYSIS PLATFORM")
    print("=" * 60)

    create_directories()

    print("\nSTEP 1: GENERATING MASTER DATA")
    generate_master_data()

    print("\nSTEP 2: GENERATING EXPOSURE AND CONVERSION EVENTS")
    generate_events()

    print("\nSTEP 3: VALIDATING DATA")
    errors = validate_data()

    if errors:
        print("\nPipeline stopped: data validation failed.")
        return

    print("\nSTEP 4: VALIDATING RANDOMIZATION")
    randomization_results = validate_randomization()

    print("\nSTEP 5: CALCULATING TREATMENT EFFECTS")
    experiment_results = calculate_metrics()

    print("\nSTEP 6: EVALUATING GUARDRAILS")
    guardrail_results = calculate_guardrails()

    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 60)

    print(f"Experiments analyzed: {len(experiment_results)}")

    print(
        "SRM alerts: "
        f"{int(randomization_results['srm_detected'].sum())}"
    )

    print(
        "Guardrail failures: "
        f"{int((guardrail_results['overall_guardrail_status'] == 'FAIL').sum())}"
    )

    print("\nPipeline completed successfully!")
    print("Check the data/raw/ and outputs/ directories.")


if __name__ == "__main__":
    run_pipeline()