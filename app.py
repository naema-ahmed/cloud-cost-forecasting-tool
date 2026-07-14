import json
import numpy as np
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from validation import spend_data_validation, commitment_data_validation
from reporting import (
    compare_statistical_methods,
    generate_cloud_report,
    suggest_method
)

st.set_page_config(
    page_title="Overcast",
    page_icon="☁️",
    layout="centered"
)

def make_json_safe(obj):
    if isinstance(obj, dict):
        return {key: make_json_safe(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(value) for value in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m")
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def add_report_display_data(report, period_spend, period_start):
    report = report.copy()

    has_history = len(period_spend) > 0

    if has_history:
        historical_dates = period_spend["year_month"].dt.strftime("%Y-%m").tolist()
        historical_spend = period_spend["spend"].tolist()
        forecast_start = period_spend["year_month"].max() + pd.DateOffset(months=1)
    else:
        historical_dates = []
        historical_spend = []
        forecast_start = period_start

    forecast_dates = pd.date_range(
        start=forecast_start,
        periods=len(report["monthly_forecasts"]),
        freq="MS"
    ).strftime("%Y-%m").tolist()

    report["historical_dates"] = historical_dates
    report["historical_spend"] = historical_spend
    report["forecast_dates"] = forecast_dates

    return make_json_safe(report)


def display_report(report):
    col1, col2, col3 = st.columns(3)

    col1.metric("Actual Cost to Date", f"${report['actual_cost_to_date']:,.2f}")
    col2.metric("Forecasted Total Spend", f"${report['forecasted_total_spend']:,.2f}")
    col3.metric("Commitment", f"${report['commitment']:,.2f}")

    col4, col5, col6 = st.columns(3)

    col4.metric("Gap", f"${report['gap']:,.2f}")
    col5.metric("Future Spend Forecast", f"${report['future_spend_total']:,.2f}")

    required_growth = report["required_monthly_growth_rate (%)"]
    col6.metric(
        "Required Monthly Growth",
        "N/A" if required_growth is None else f"{required_growth:.2f}%"
    )

    st.write(f"**Status:** {report['status']}")
    st.write(f"**Method used:** {report['method_used']}")
    st.write(f"**Period:** {report['period_start']} to {report['period_end']}")
    st.write(f"**Months remaining:** {report['months_remaining']}")

    st.subheader("Monthly Forecast")

    forecast_df = pd.DataFrame({
        "month": report["forecast_dates"],
        "forecasted_spend": report["monthly_forecasts"]
    })

    st.dataframe(forecast_df)

    st.subheader("Forecast Plot")

    fig, ax = plt.subplots(figsize=(10, 5))

    if len(report["historical_dates"]) > 0:
        ax.plot(
            pd.to_datetime(report["historical_dates"]),
            report["historical_spend"],
            label="Historical"
        )

    ax.plot(
        pd.to_datetime(report["forecast_dates"]),
        report["monthly_forecasts"],
        label="Forecast"
    )

    ax.set_title(f"{report['cloud']} Historical and Forecasted Cloud Spend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Cost")
    ax.legend()
    ax.tick_params(axis="x", rotation=45)

    st.pyplot(fig)

    st.subheader("Cumulative Spend vs Commitment")

    fig, ax = plt.subplots(figsize=(10, 5))

    historical_cumulative = pd.Series(report["historical_spend"]).cumsum().tolist()

    if len(report["historical_dates"]) > 0:
        ax.plot(
            pd.to_datetime(report["historical_dates"]),
            historical_cumulative,
            linewidth=2,
            label="Historical cumulative"
        )
        cumulative_start = historical_cumulative[-1]
    else:
        cumulative_start = 0

    forecast_cumulative = (
        cumulative_start + pd.Series(report["monthly_forecasts"]).cumsum()
    ).tolist()

    ax.plot(
        pd.to_datetime(report["forecast_dates"]),
        forecast_cumulative,
        linewidth=2,
        label="Forecast cumulative"
    )

    ax.axhline(
        y=report["commitment"],
        linestyle="--",
        linewidth=2,
        label="Commitment"
    )

    ax.set_title(f"{report['cloud']}: Cumulative Spend vs Commitment")
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative Spend")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()

    st.pyplot(fig)

    with st.expander("View raw report data"):
        st.json(report)

st.title("Overcast")
st.caption("A cloud cost forecasting tool.")

st.subheader("Load Saved Report")

saved_report_file = st.file_uploader(
    "Upload saved report JSON",
    type=["json"]
)

if saved_report_file:
    saved_report = json.load(saved_report_file)
    display_report(saved_report)

st.subheader("1. Upload Data")

spend_file = st.file_uploader("Upload spend data CSV", type=["csv"])
commitment_file = st.file_uploader("Upload commitment data CSV", type=["csv"])

if spend_file and commitment_file:
    spend_data = spend_data_validation(pd.read_csv(spend_file))
    commitments_data = commitment_data_validation(pd.read_csv(commitment_file))

    st.success("Data loaded successfully.")

    with st.expander("View uploaded spend data"):
        st.dataframe(spend_data)

    with st.expander("View uploaded commitment data"):
        st.dataframe(commitments_data)

    selected_cloud = st.selectbox(
        "Select cloud provider",
        commitments_data["cloud"].unique()
    )

    cloud_commitment = commitments_data[
        commitments_data["cloud"] == selected_cloud
    ].iloc[0]

    period_start = cloud_commitment["period_start"]
    period_end = cloud_commitment["period_end"]

    period_spend = spend_data[
        (spend_data["cloud"] == selected_cloud) &
        (spend_data["year_month"] >= period_start) &
        (spend_data["year_month"] <= period_end)
    ]

    has_historical_data = len(period_spend) > 0

    selected_method = None
    project_adjustments = []

    st.subheader("2. Forecast Setup")

    if has_historical_data:
        st.write("Historical spend data was found for this cloud and commitment period.")

        st.subheader("Forecast Method Comparison")

        comparison_df = compare_statistical_methods(
            spend_data=spend_data,
            commitments=commitments_data,
            cloud=selected_cloud
        )

        st.dataframe(comparison_df)

        spend_series = period_spend["spend"]
        has_seasonality = st.checkbox("Use seasonal forecasting if data appears seasonal", 
                                      value=False,
                                      help="Allows Holt-Winters forecasting when at least 24 months of data are available. Use if a seasonal pattern is expected."
                                      )
        
        suggestion = suggest_method(spend_series, has_seasonality=has_seasonality)

        st.subheader("Suggested Method")
        st.write(f"**Suggested method:** {suggestion['suggested_method']}")
        st.write(f"**Reason:** {suggestion['reason']}")

        with st.expander("View diagnostics"):
            st.json(suggestion["diagnostics"])

        method_options = [
            "run_rate_forecast",
            "moving_average_forecast",
            "historic_growth_forecast",
            "single_exponential_smoothing_forecast",
            "holt_double_exponential_smoothing_forecast",
            "holtwinters_triple_exponential_smoothing_forecast"
        ]

        default_index = (
            method_options.index(suggestion["suggested_method"])
            if suggestion["suggested_method"] in method_options
            else 0
        )

        selected_method = st.selectbox(
            "Choose method for final report",
            method_options,
            index=default_index
        )

        apply_project_adjustments = st.checkbox(
            "Apply planned project adjustment"
        )

        if apply_project_adjustments:
            months_remaining_preview = (
                (period_end.year - period_spend["year_month"].max().year) * 12
                + (period_end.month - period_spend["year_month"].max().month)
            )

            future_months = pd.date_range(
                start=period_spend["year_month"].max() + pd.DateOffset(months=1),
                periods=months_remaining_preview,
                freq="MS"
            )

            adjustment_df = pd.DataFrame({
                "month": future_months.strftime("%Y-%m"),
                "project_adjustment": [0.0] * months_remaining_preview
            })

            edited_adjustment_df = st.data_editor(
                adjustment_df,
                use_container_width=True,
                disabled=["month"]
            )

            project_adjustments = edited_adjustment_df["project_adjustment"].tolist()

    else:
        st.warning(
            "No historical spend data was found for this cloud and commitment period. At least one month of historical spend data is required to generate a forecast."
        )


    st.subheader("3. Final Report")

    if st.button("Generate Report"):
        report = generate_cloud_report(
            spend_data=spend_data,
            commitments=commitments_data,
            cloud=selected_cloud,
            selected_method=selected_method,
            project_adjustments=project_adjustments
        )

        if "status" in report and report["status"] in [
            "Insufficient data",
            "Forecast failed"
        ]:
            st.error(report["message"])
            st.json(report)

        else:
            report = add_report_display_data(
            report=report,
            period_spend=period_spend,
            period_start=period_start
            )

            display_report(report)

            report_json = json.dumps(report, indent=4)

            st.download_button(
                label="Download Report",
                data=report_json,
                file_name=f"Overcast_{selected_cloud}_report.json",
                mime="application/json"
            )