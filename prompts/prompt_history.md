# AI Prompt History — Experiment Analysis Platform

## Purpose

This document records the AI-assisted development activities used to build the Experiment Analysis Platform. It summarizes the prompts and tasks used during development to support transparency and reproducibility.

**Note:** The entries below summarize the development requests. They are not claimed to be exact verbatim copies of every original prompt.

## 1. Project Architecture and Planning

**Prompt summary:** Design an end-to-end experiment analysis platform that supports experiment design, randomization validation, guardrail metrics, treatment-effect estimation, traceability, and measurable outputs.

**Development activity:**

* Defined project scope and major components.
* Organized the Python project structure.
* Identified the primary experiment entities and workflows.
* Planned a synthetic-data-based implementation.

## 2. Synthetic Data Generation

**Prompt summary:** Implement reproducible synthetic data generation for experiments, variants, eligible users, assignments, exposure events, and conversion events.

**Development activity:**

* Configured a fixed random seed of `20261022`.
* Generated 10 experiments and 20 variants.
* Generated 50,000 eligible synthetic users.
* Generated 500,000 assignments.
* Generated exposure and conversion events.
* Used separate generation modules for master data and events.

## 3. Data Validation

**Prompt summary:** Strengthen data validation to detect missing and duplicate identifiers, invalid references, assignment inconsistencies, ineligible assignments, invalid timestamps, and conversion-window violations.

**Development activity:**

* Added primary-key uniqueness checks.
* Added foreign-key and entity-consistency checks.
* Added eligibility and allocation checks.
* Added experiment date and event chronology checks.
* Added conversion-value validation.
* Added an automated test for conversions outside the experiment window.

## 4. Randomization Validation

**Prompt summary:** Evaluate control and treatment assignment balance and identify potential sample-ratio mismatch.

**Development activity:**

* Compared observed assignments with expected allocations.
* Calculated chi-square statistics and p-values.
* Produced experiment-level randomization results.

## 5. Treatment-Effect Analysis

**Prompt summary:** Calculate control and treatment conversion rates, absolute and relative effects, confidence intervals, and statistical significance.

**Development activity:**

* Implemented experiment-level conversion analysis.
* Used assignment-based analysis for intention-to-treat estimates.
* Exported variant-level metrics and experiment results.

## 6. Guardrail Metrics

**Prompt summary:** Evaluate critical metrics for regressions and identify experiments that should not be recommended despite positive primary-metric results.

**Development activity:**

* Implemented payment-error and refund-rate comparisons.
* Applied configured thresholds.
* Generated guardrail pass/fail decisions.

## 7. Anomaly Detection

**Prompt summary:** Build and test anomaly detection for multiple variant assignments, exposure before assignment, invalid conversion windows, and metric-definition changes.

**Development activity:**

* Created synthetic anomaly cases.
* Implemented detection logic.
* Added automated tests for supported anomaly types.

**Known limitation:** The sample-ratio-mismatch anomaly detector was not detecting the intended case during development. Four anomaly types were retained as the currently tested set.

## 8. Automated Testing

**Prompt summary:** Create automated tests for data generation and anomaly-detection behavior, and verify the conversion-window validation rule.

**Development activity:**

* Added tests for experiment, variant, audience, and assignment generation.
* Added tests for supported anomaly types.
* Added a test for out-of-window conversions.

**Observed result:** Nine tests passed during development.

## 9. Reproducibility

**Prompt summary:** Verify that the synthetic data-generation process produces identical output files across repeated runs.

**Development activity:**

* Implemented SHA-256 checksum calculation.
* Regenerated the six source datasets twice.
* Compared checksums across runs.

**Observed result:** All six source CSV checksums matched.

## 10. Data Export

**Prompt summary:** Export generated datasets into JSON and SQL-compatible formats and verify the SQLite database.

**Development activity:**

* Exported six JSON datasets.
* Created `outputs/experiment_analysis.db`.
* Created `outputs/seed.sql`.
* Created a database verification script.
* Verified six tables and 500,000 assignment records.

**Known limitation:** The current SQLite export does not explicitly enforce all primary-key and foreign-key constraints.

## 11. Source Manifest

**Prompt summary:** Create a manifest containing dataset names, paths, columns, record counts, configuration, file sizes, and SHA-256 checksums.

**Development activity:**

* Recorded the random seed and dataset mode.
* Documented the six source datasets.
* Calculated checksums for traceability.

## 12. Documentation

**Prompt summary:** Document the project architecture, setup instructions, analysis methodology, dataset schemas, validation rules, and implementation limitations.

**Development activity:**

* Prepared the project README.
* Prepared the data dictionary.
* Documented the logical database schema.

## 13. Dashboard

**Prompt summary:** Build a Streamlit dashboard for viewing experiment results, randomization checks, and guardrail outcomes.

**Development activity:**

* Added experiment selection.
* Displayed conversion metrics and treatment comparisons.
* Displayed randomization and guardrail results.

## 14. Responsible AI Use

AI assistance was used to support planning, implementation, debugging, testing, and documentation. The developer remains responsible for reviewing the generated code, understanding the implementation, running the tests, and verifying the submitted results.

For a verbatim prompt archive, retain the original prompts from the development conversation rather than treating this reconstructed summary as an exact transcript.
