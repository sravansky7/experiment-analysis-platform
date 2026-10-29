import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from src.config import OUTPUT_DIR

st.set_page_config(
    page_title="Experiment Analysis Platform",
    page_icon="📊",
    layout="wide",
)

st.title("Experiment Analysis Platform")
st.caption(
    "Experiment monitoring, randomization validation, "
    "treatment effects, and guardrail analysis."
)

# Load generated results
@st.cache_data
def load_results():
    results = pd.read_csv(
        OUTPUT_DIR / "experiment_results.csv"
    )
    randomization = pd.read_csv(
        OUTPUT_DIR / "randomization_results.csv"
    )
    guardrails = pd.read_csv(
        OUTPUT_DIR / "guardrail_results.csv"
    )
    return results, randomization, guardrails


try:
    results, randomization, guardrails = load_results()
except FileNotFoundError:
    st.error(
        "Results not found. Run `python main.py` first."
    )
    st.stop()

# Sidebar
st.sidebar.header("Experiment Filters")

experiment_options = results["experiment_id"].tolist()

selected_experiment = st.sidebar.selectbox(
    "Select an experiment",
    ["All Experiments"] + experiment_options,
)

if selected_experiment == "All Experiments":
    filtered_results = results.copy()
    filtered_randomization = randomization.copy()
    filtered_guardrails = guardrails.copy()
else:
    filtered_results = results[
        results["experiment_id"] == selected_experiment
    ]
    filtered_randomization = randomization[
        randomization["experiment_id"] == selected_experiment
    ]
    filtered_guardrails = guardrails[
        guardrails["experiment_id"] == selected_experiment
    ]

# KPI cards
total_experiments = len(filtered_results)

significant_count = int(
    filtered_results["statistically_significant"].sum()
)

srm_alerts = int(
    filtered_randomization["srm_detected"].sum()
)

guardrail_failures = int(
    (
        filtered_guardrails["overall_guardrail_status"] == "FAIL"
    ).sum()
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Experiments", total_experiments)
col2.metric("Significant Results", significant_count)
col3.metric("SRM Alerts", srm_alerts)
col4.metric("Guardrail Failures", guardrail_failures)

st.divider()

# Treatment effects
st.subheader("Treatment Effect Analysis")

display_results = filtered_results.copy()

display_results["Control Conversion (%)"] = (
    display_results["control_conversion_rate"] * 100
)

display_results["Treatment Conversion (%)"] = (
    display_results["treatment_conversion_rate"] * 100
)

display_results["Absolute Effect (pp)"] = (
    display_results["absolute_effect"] * 100
)

st.dataframe(
display_results[
[
"experiment_id",
"Control Conversion (%)",
"Treatment Conversion (%)",
"Absolute Effect (pp)",
"p_value",
"statistically_significant",
]
].style.format(
{
"Control Conversion (%)": "{:.3f}",
"Treatment Conversion (%)": "{:.3f}",
"Absolute Effect (pp)": "{:.3f}",
"p_value": "{:.3e}",
}
),
use_container_width=True,
hide_index=True,
)



# Conversion rate chart
st.subheader("Control vs Treatment Conversion Rates")

fig, ax = plt.subplots(figsize=(12, 5))

x = range(len(display_results))
width = 0.35

ax.bar(
    [i - width / 2 for i in x],
    display_results["Control Conversion (%)"],
    width,
    label="Control",
)

ax.bar(
    [i + width / 2 for i in x],
    display_results["Treatment Conversion (%)"],
    width,
    label="Treatment",
)

ax.set_xticks(list(x))
ax.set_xticklabels(
    display_results["experiment_id"],
    rotation=45,
    ha="right",
)

ax.set_ylabel("Conversion Rate (%)")
ax.set_title("Conversion Rate by Experiment")
ax.legend()
fig.tight_layout()

st.pyplot(fig)
plt.close(fig)

# Randomization validation
st.subheader("Randomization Validation")

st.dataframe(
    filtered_randomization,
    use_container_width=True,
    hide_index=True,
)

# Guardrail analysis
st.subheader("Guardrail Monitoring")

st.dataframe(
    filtered_guardrails,
    use_container_width=True,
    hide_index=True,
)

failed_guardrails = filtered_guardrails[
    filtered_guardrails["overall_guardrail_status"] == "FAIL"
]

if not failed_guardrails.empty:
    st.error(
        f"{len(failed_guardrails)} experiment(s) have "
        "guardrail failures. Review these before interpreting "
        "the treatment results."
    )
else:
    st.success("No guardrail failures detected in this selection.")

st.caption(
    "Results are based on synthetic data. Statistical significance "
    "does not establish business significance or guarantee "
    "causality when experiment assumptions are violated."
)

# Treatment Effect Confidence Interval Chart

st.subheader("📊 Treatment Effects with 95% Confidence Intervals")

chart_data = filtered_results.copy()

chart_data["Effect (pp)"] = chart_data["absolute_effect"] * 100
chart_data["CI Lower (pp)"] = (
chart_data["confidence_interval_lower"] * 100
)
chart_data["CI Upper (pp)"] = (
chart_data["confidence_interval_upper"] * 100
)

chart_data = chart_data.sort_values("Effect (pp)")

chart_data["CI Error Lower"] = (
chart_data["Effect (pp)"] - chart_data["CI Lower (pp)"]
)
chart_data["CI Error Upper"] = (
chart_data["CI Upper (pp)"] - chart_data["Effect (pp)"]
)

st.caption(
"Points represent the estimated treatment effect. "
"Horizontal bars show 95% confidence intervals. "
"The zero line represents no difference between treatment and control."
)

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))

ax.errorbar(
chart_data["Effect (pp)"],
chart_data["experiment_id"],
xerr=[
chart_data["CI Error Lower"],
chart_data["CI Error Upper"],
],
fmt="o",
capsize=4,
)

ax.axvline(x=0, linestyle="--")
ax.set_xlabel("Absolute Treatment Effect (percentage points)")
ax.set_ylabel("Experiment")
ax.set_title("Treatment Effect Estimates with 95% Confidence Intervals")
ax.grid(axis="x", alpha=0.3)

fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

# Anomaly Detection Dashboard
st.divider()
st.header("🚨 Anomaly Detection")

anomaly_file = OUTPUT_DIR / "anomaly_detection_report.csv"

if anomaly_file.exists():
    anomaly_df = pd.read_csv(anomaly_file)

    total_anomalies = len(anomaly_df)
    anomaly_types = (
        anomaly_df["anomaly_type"].nunique()
        if "anomaly_type" in anomaly_df.columns
        else 0
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Anomalies Detected", total_anomalies)

    with col2:
        st.metric("Anomaly Types", anomaly_types)

    if "anomaly_type" in anomaly_df.columns:
        st.subheader("Anomaly Breakdown")

        anomaly_counts = (
            anomaly_df["anomaly_type"]
            .value_counts()
            .rename_axis("Anomaly Type")
            .reset_index(name="Count")
        )

        st.bar_chart(
            anomaly_counts,
            x="Count",
            y="Anomaly Type",
            horizontal=True,
        )

    st.subheader("Detailed Anomaly Report")
    st.dataframe(
        anomaly_df,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.warning(
        "Anomaly report not found. Run the anomaly detector first."
    )