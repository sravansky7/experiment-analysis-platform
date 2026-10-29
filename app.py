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
    ].round(3),
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