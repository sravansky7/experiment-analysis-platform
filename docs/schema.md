# Experiment Analysis Platform — Database Schema

## 1. Overview

The Experiment Analysis Platform uses six primary data tables to represent experiments, variants, audience members, assignments, exposure events, and conversion events.

The source datasets are stored as CSV files under `data/raw/` and exported to the SQLite database `outputs/experiment_analysis.db`.

**Important:** This document describes the logical schema and intended relationships. The current SQLite export creates tables from CSV files without explicitly enforcing all primary-key and foreign-key constraints.

## 2. Entity Relationship Diagram

```text
+------------------+
|    experiments   |
+------------------+
| PK experiment_id |
+------------------+
         |
         | 1:N
         v
+------------------+
|     variants     |
+------------------+
| PK variant_id    |
| FK experiment_id |
+------------------+

+------------------+       +----------------------+
| audience_members |       |      experiments     |
+------------------+       +----------------------+
| PK user_id       |                |
+------------------+                |
         |                           |
         | 1:N                       | 1:N
         v                           v
+------------------------------------------+
|               assignments                |
+------------------------------------------+
| PK assignment_id                         |
| FK experiment_id                         |
| FK user_id                               |
| FK variant_id                            |
+------------------------------------------+
         |
         | 1:N
         +--------------------+
         |                    |
         v                    v
+-------------------+  +---------------------+
|  exposure_events  |  |  conversion_events   |
+-------------------+  +---------------------+
| PK exposure_id    |  | PK conversion_id    |
| FK assignment_id  |  | FK assignment_id    |
| experiment_id     |  | experiment_id       |
| user_id           |  | user_id             |
| variant_id        |  | variant_id          |
| exposed_at        |  | converted_at        |
+-------------------+  | conversion_value    |
                       +---------------------+
```

**Notation:**

* PK: Primary key
* FK: Foreign key
* 1:N: One-to-many relationship

## 3. Table Specifications

### 3.1 experiments

**Source:** `data/raw/experiments.csv`

| Column            | Type      | Constraint or purpose          |
| ----------------- | --------- | ------------------------------ |
| `experiment_id`   | TEXT      | Primary key                    |
| `experiment_name` | TEXT      | Human-readable experiment name |
| `hypothesis`      | TEXT      | Experiment hypothesis          |
| `primary_metric`  | TEXT      | Primary evaluation metric      |
| `status`          | TEXT      | Lifecycle status               |
| `start_date`      | DATE/TEXT | Experiment start date          |
| `end_date`        | DATE/TEXT | Experiment end date            |
| `random_seed`     | INTEGER   | Experiment-specific seed       |

### 3.2 variants

**Source:** `data/raw/variants.csv`

| Column          | Type | Constraint or purpose        |
| --------------- | ---- | ---------------------------- |
| `variant_id`    | TEXT | Primary key                  |
| `experiment_id` | TEXT | References an experiment     |
| `variant_name`  | TEXT | Control or Treatment         |
| `allocation`    | REAL | Expected allocation fraction |

**Integrity rules:**

* Every variant belongs to an existing experiment.
* Each experiment's variant allocations sum to 1.
* Allocation values are greater than 0 and at most 1.

### 3.3 audience_members

**Source:** `data/raw/audience_members.csv`

| Column     | Type         | Constraint or purpose  |
| ---------- | ------------ | ---------------------- |
| `user_id`  | TEXT         | Primary key            |
| `age`      | INTEGER      | Synthetic user age     |
| `country`  | TEXT         | Synthetic user country |
| `eligible` | BOOLEAN/TEXT | Assignment eligibility |

**Integrity rule:** Only eligible users may be assigned.

### 3.4 assignments

**Source:** `data/raw/assignments.csv`

| Column          | Type           | Constraint or purpose         |
| --------------- | -------------- | ----------------------------- |
| `assignment_id` | TEXT           | Primary key                   |
| `experiment_id` | TEXT           | References an experiment      |
| `user_id`       | TEXT           | References an audience member |
| `variant_id`    | TEXT           | References a variant          |
| `assigned_at`   | TIMESTAMP/TEXT | Assignment timestamp          |

**Integrity rules:**

* The experiment, user, and variant must exist.
* The selected variant must belong to the specified experiment.
* A user may have only one variant assignment per experiment.

### 3.5 exposure_events

**Source:** `data/raw/exposure_events.csv`

| Column          | Type           | Constraint or purpose    |
| --------------- | -------------- | ------------------------ |
| `exposure_id`   | TEXT           | Primary key              |
| `experiment_id` | TEXT           | Associated experiment    |
| `assignment_id` | TEXT           | References an assignment |
| `user_id`       | TEXT           | Associated user          |
| `variant_id`    | TEXT           | Associated variant       |
| `exposed_at`    | TIMESTAMP/TEXT | Exposure timestamp       |

**Integrity rules:**

* The assignment must exist.
* The event's experiment, user, and variant must match its assignment.
* Exposure must not precede assignment.

### 3.6 conversion_events

**Source:** `data/raw/conversion_events.csv`

| Column             | Type           | Constraint or purpose      |
| ------------------ | -------------- | -------------------------- |
| `conversion_id`    | TEXT           | Primary key                |
| `experiment_id`    | TEXT           | Associated experiment      |
| `assignment_id`    | TEXT           | References an assignment   |
| `user_id`          | TEXT           | Associated user            |
| `variant_id`       | TEXT           | Associated variant         |
| `converted_at`     | TIMESTAMP/TEXT | Conversion timestamp       |
| `conversion_value` | REAL           | Synthetic conversion value |

**Integrity rules:**

* The assignment must exist.
* The event's experiment, user, and variant must match its assignment.
* Conversion must occur after assignment and within the experiment date window.
* Conversion value must be numeric and non-negative.

## 4. Relationship Summary

| Parent entity    | Child entity      | Relationship | Join key        |
| ---------------- | ----------------- | ------------ | --------------- |
| experiments      | variants          | One-to-many  | `experiment_id` |
| experiments      | assignments       | One-to-many  | `experiment_id` |
| audience_members | assignments       | One-to-many  | `user_id`       |
| variants         | assignments       | One-to-many  | `variant_id`    |
| assignments      | exposure_events   | One-to-many  | `assignment_id` |
| assignments      | conversion_events | One-to-many  | `assignment_id` |

The event tables also store experiment, user, and variant identifiers for analysis and traceability. Those values must remain consistent with the referenced assignment.

## 5. Validation Requirements

The validation module checks the generated datasets for:

1. Missing and duplicate primary keys.
2. References to nonexistent experiments, variants, users, or assignments.
3. Variant-to-experiment consistency.
4. Assignment-to-event consistency.
5. Ineligible users receiving assignments.
6. Duplicate assignments within an experiment.
7. Invalid experiment date ranges.
8. Invalid variant allocations.
9. Events occurring before assignment.
10. Conversions outside the experiment date window.
11. Invalid or negative conversion values.

## 6. Database Export

The export module creates:

* `outputs/experiment_analysis.db`
* `outputs/seed.sql`

The SQLite database currently contains the six source tables.

**Current limitation:** The database export is created from DataFrames, so explicit database-level primary-key, foreign-key, uniqueness, and check constraints are not yet implemented. The validation module checks many of these rules before analysis, but that is not equivalent to enforcing them inside SQLite.

## 7. Current Dataset Scale

| Entity            | Current record count |
| ----------------- | -------------------: |
| Experiments       |                   10 |
| Variants          |                   20 |
| Audience members  |               50,000 |
| Assignments       |              500,000 |
| Exposure events   |              450,238 |
| Conversion events |               55,194 |

These counts describe the current generated dataset and may change if the configuration or generation logic changes.

## 8. Future Improvements

* Enforce primary keys and foreign keys directly in SQLite.
* Add uniqueness constraints for user assignments per experiment.
* Add database-level checks for valid allocation values and conversion values.
* Represent metric definitions and guardrail results as explicit entities.
* Add schema-version metadata and migration support.
* Test database constraints using intentionally invalid records.

---

**Schema status:** Logical schema documented; explicit relational constraints in SQLite remain a planned improvement.
