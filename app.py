import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from validation import spend_data_validation, commitment_data_validation
from reporting import (
    compare_statistical_methods,
    generate_cloud_report,
    suggest_method
)

st.title("Cloud Cost Commitment Forecasting Tool")

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

    expected_monthly_spend = None
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
        has_seasonality = st.checkbox(
            "Use seasonal forecasting if data appears seasonal",
            value=False
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

            monthly_project_adjustment = st.number_input(
                "Additional monthly project spend",
                min_value=0.0,
                value=0.0
            )

            project_adjustments = [
                monthly_project_adjustment
            ] * months_remaining_preview

    else:
        st.warning(
            "No historical spend data was found for this cloud and commitment period."
        )

        expected_monthly_spend = st.number_input(
            "Enter expected monthly spend",
            min_value=0.0,
            value=0.0
        )

        selected_method = "monthly_expectation_based_forecast"

    st.subheader("3. Final Report")

    if st.button("Generate Report"):
        report = generate_cloud_report(
            spend_data=spend_data,
            commitments=commitments_data,
            cloud=selected_cloud,
            selected_method=selected_method,
            expected_monthly_spend=expected_monthly_spend,
            project_adjustments=project_adjustments
        )

        if "status" in report and report["status"] in [
            "Insufficient data",
            "Forecast failed"
        ]:
            st.error(report["message"])
            st.json(report)

        else:
            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Actual Cost to Date",
                f"${report['actual_cost_to_date']:,.2f}"
            )

            col2.metric(
                "Forecasted Total Spend",
                f"${report['forecasted_total_spend']:,.2f}"
            )

            col3.metric(
                "Commitment",
                f"${report['commitment']:,.2f}"
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "Gap",
                f"${report['gap']:,.2f}"
            )

            col5.metric(
                "Future Spend Forecast",
                f"${report['future_spend_total']:,.2f}"
            )

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
                "forecast_month_number": range(
                    1,
                    len(report["monthly_forecasts"]) + 1
                ),
                "forecasted_spend": report["monthly_forecasts"]
            })

            st.dataframe(forecast_df)

            ## Forecast Plot
            st.subheader("Forecast Plot")

            historical_plot_df = period_spend[["year_month", "spend"]].copy()
            historical_plot_df = historical_plot_df.rename(columns={"spend": "cost"})

            last_spend_month = historical_plot_df["year_month"].max()

            forecast_months = pd.date_range(
                start=last_spend_month + pd.DateOffset(months=1),
                periods=len(report["monthly_forecasts"]),
                freq="MS"
            )

            forecast_plot_df = pd.DataFrame({
                "year_month": forecast_months,
                "cost": report["monthly_forecasts"]
            })

            fig, ax = plt.subplots(figsize=(10, 5))

            ax.plot(
                historical_plot_df["year_month"],
                historical_plot_df["cost"],
                label="Historical"
            )  

            ax.plot(
                forecast_plot_df["year_month"],
                forecast_plot_df["cost"],
                label="Forecast"
            )

            ax.set_title(f"{selected_cloud} Historical and Forecasted Cloud Spend")
            ax.set_xlabel("Month")
            ax.set_ylabel("Cost")
            ax.legend()
            ax.tick_params(axis="x", rotation=45)

            st.pyplot(fig)

            ## cumulative plot
            import matplotlib.pyplot as plt

            st.subheader("Cumulative Spend vs Commitment")

            # Historical cumulative spend
            historical_df = period_spend[["year_month", "spend"]].copy()
            historical_df["cumulative_spend"] = historical_df["spend"].cumsum()

            # Forecast months
            last_month = historical_df["year_month"].iloc[-1]

            forecast_months = pd.date_range(
                start=last_month + pd.DateOffset(months=1),
                periods=len(report["monthly_forecasts"]),
                freq="MS"
            )

            # Forecast cumulative spend
            forecast_df = pd.DataFrame({
                "year_month": forecast_months,
                "monthly_spend": report["monthly_forecasts"]
            })

            forecast_df["cumulative_spend"] = (
                historical_df["cumulative_spend"].iloc[-1]
                + forecast_df["monthly_spend"].cumsum()
            )

            # Plot
            fig, ax = plt.subplots(figsize=(10,5))

            # Historical cumulative
            ax.plot(
                historical_df["year_month"],
                historical_df["cumulative_spend"],
                linewidth=2,
                label="Historical cumulative"
            )

            # Forecast cumulative
            ax.plot(
                forecast_df["year_month"],
                forecast_df["cumulative_spend"],
                linewidth=2,
                label="Forecast cumulative"
            )

            # Commitment line
            ax.axhline(
                y=report["commitment"],
                linestyle="--",
                linewidth=2,
                label="Commitment"
            )

            ax.set_title(f"{selected_cloud}: Cumulative Spend vs Commitment")
            ax.set_xlabel("Month")
            ax.set_ylabel("Cumulative Spend")
            ax.tick_params(axis="x", rotation=45)
            ax.legend()

            st.pyplot(fig)



            with st.expander("View raw report data"):
                st.json(report)