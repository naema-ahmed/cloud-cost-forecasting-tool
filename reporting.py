import pandas as pd
import numpy as np

from validation import spend_data_validation, commitment_data_validation
from forecasting import (
    run_rate_forecast,
    moving_average_forecast,
    historic_growth_forecast,
    single_exponential_smoothing_forecast,
    holt_double_exponential_smoothing_forecast,
    holtwinters_triple_exponential_smoothing_forecast,
    monthly_expectation_based_forecast,
    project_expectation_forecast
)


def forecast_gap(actual_cost_to_date, future_spend_total, commitment):

    forecasted_total_spend = actual_cost_to_date + future_spend_total 
    gap = commitment - forecasted_total_spend

    if gap>0:
        status = "Forecast falls short"
    elif gap==0:
        status = "Forecast meets commitment"
    else:
        status= "Forecast exceeds commitment"
    return {
    "actual_cost_to_date": actual_cost_to_date, "future_spend_total":future_spend_total,
    "forecasted_total_spend":forecasted_total_spend, "commitment":commitment, "gap":gap, "status":status }

def required_growth_rate(current_monthly_spend, actual_cost_to_date, commitment, months_remaining):
    target_future_spend = commitment - actual_cost_to_date
    if target_future_spend <=0:
        return 0
    if (target_future_spend<=0) or (months_remaining <=0):
        return None

    def future_total(r):
        total = 0
        for i in range(months_remaining):
            total += current_monthly_spend * ((1+r)**i) 
        return total
    low = -0.99
    high = 10
    for i in range(100): # bisection method / binary search using N_iterations = 100
        mid = (low + high) / 2
        if future_total(mid) < target_future_spend:
            low = mid
        else:
            high = mid
    return high*100

def analyze_spend_diagnostics(spend):
    spend = pd.Series(spend).dropna()
    n = len(spend)

    if n == 0:
        return {
            "n": 0,
            "is_stable": False,
            "is_volatile": False,
            "has_trend": False,
            "has_seasonality": False,
            "recent_level_off": False,
            "coefficient_of_variation": None,
            "relative_volatility_std": None,
            "relative_slope": None,
            "seasonal_strength": None
        }

    mean_spend = spend.mean()
    std_spend = spend.std()

    coefficient_of_variation = (
        std_spend / mean_spend
        if mean_spend != 0
        else np.inf
    )

    x = np.arange(n)

    if n >= 3:
        slope = np.polyfit(x, spend, 1)[0]
        relative_slope = slope / mean_spend if mean_spend != 0 else 0
    else:
        relative_slope = 0

    monthly_changes = spend.diff().dropna()

    if len(monthly_changes) >= 2:

        relative_volatility_std = (
            monthly_changes.std() / mean_spend
            if mean_spend != 0
            else 0
        )
    else:
        relative_volatility_std = 0

    has_trend = abs(relative_slope) >= 0.015
    is_volatile = relative_volatility_std > 1.0

    is_stable = (
        coefficient_of_variation < 0.08
        and abs(relative_slope) < 0.015
        and not is_volatile
    )

    seasonal_strength = None
    has_seasonality = False

    if n >= 24:
        month_index = np.arange(n) % 12

        seasonal_table = pd.DataFrame({
            "month_index": month_index,
            "spend": spend.values
        })

        monthly_means = seasonal_table.groupby("month_index")["spend"].mean()

        seasonal_strength = (
            monthly_means.std() / mean_spend
            if mean_spend != 0
            else 0
        )

        has_seasonality = seasonal_strength > 0.08

    recent_level_off = False

    if n >= 8:
        first_half = spend.iloc[: n // 2]
        second_half = spend.iloc[n // 2 :]

        first_slope = np.polyfit(np.arange(len(first_half)), first_half, 1)[0]
        second_slope = np.polyfit(np.arange(len(second_half)), second_half, 1)[0]

        first_relative_slope = (
            first_slope / first_half.mean()
            if first_half.mean() != 0
            else 0
        )

        second_relative_slope = (
            second_slope / second_half.mean()
            if second_half.mean() != 0
            else 0
        )

        recent_level_off = (
            first_relative_slope > 0.02
            and abs(second_relative_slope) < 0.01
        )

    return {
        "n": n,
        "is_stable": is_stable,
        "is_volatile": is_volatile,
        "has_trend": has_trend,
        "has_seasonality": has_seasonality,
        "recent_level_off": recent_level_off,
        "coefficient_of_variation": coefficient_of_variation,
        "relative_volatility_std": relative_volatility_std,
        "relative_slope": relative_slope,
        "seasonal_strength": seasonal_strength
    }


def suggest_method(spend, has_project_estimations=False, expected_monthly_spend=None, has_seasonality=False):
    diagnostics = analyze_spend_diagnostics(spend)

    n = diagnostics["n"]

    if has_project_estimations:
        return {
            "suggested_method": "project_expectation_forecast",
            "reason": "Project/business estimates were provided, so the forecast should incorporate known future changes.",
            "diagnostics": diagnostics
        }

    if n == 0 and expected_monthly_spend is not None:
        return {
            "suggested_method": "monthly_expectation_based_forecast",
            "reason": "No historical spend data is available, but an expected monthly spend was provided.",
            "diagnostics": diagnostics
        }

    if n == 0:
        return {
            "suggested_method": "insufficient_data",
            "reason": "No historical spend data or business estimate is available.",
            "diagnostics": diagnostics
        }

    if n < 3:
        return {
            "suggested_method": "run_rate_forecast",
            "reason": "Very limited historical data is available, so a simple run-rate forecast is the safest option.",
            "diagnostics": diagnostics
        }

    if has_seasonality and n>=24:
        return {
            "suggested_method": "holtwinters_triple_exponential_smoothing_forecast",
            "reason": "User specified data is seasonal, so Holt-Winters is preferred.",
            "diagnostics": diagnostics
        }

    if diagnostics["recent_level_off"]:
        return {
            "suggested_method": "single_exponential_smoothing_forecast",
            "reason": "Spend appears to have grown earlier but recently stabilized, so SES is preferred.",
            "diagnostics": diagnostics
        }
    
    if diagnostics["has_trend"] and not diagnostics["is_volatile"]:
        return {
            "suggested_method": "holt_double_exponential_smoothing_forecast",
            "reason": "A trend signal was detected without high volatility, so Holt's trend method is preferred.",
            "diagnostics": diagnostics
        }

    if diagnostics["is_stable"]:
        return {
            "suggested_method": "single_exponential_smoothing_forecast",
            "reason": "Spend appears stable, so SES is preferred as a simple level-based forecast.",
            "diagnostics": diagnostics
        }

    if diagnostics["is_volatile"]:
        return {
            "suggested_method": "moving_average_forecast",
            "reason": "Spend is volatile, so a moving average is preferred to smooth short-term fluctuations.",
            "diagnostics": diagnostics
        }


    return {
        "suggested_method": "moving_average_forecast",
        "reason": "No strong trend, seasonality, or stabilization pattern was detected, so moving averageis used as a baseline.",
        "diagnostics": diagnostics
    }


def generate_cloud_report(spend_data, commitments, cloud, project_adjustments=None, expected_monthly_spend=None,  selected_method=None,):
    
    project_adjustments = project_adjustments or []

    spend_data = spend_data_validation(spend_data)
    commitments = commitment_data_validation(commitments)

    cloud_spend = spend_data[spend_data["cloud"] == cloud]
    cloud_commitment = commitments[commitments["cloud"] == cloud].iloc[0]

    period_start = cloud_commitment["period_start"]
    period_end = cloud_commitment["period_end"]
    commitment = cloud_commitment["commitment"]

    period_spend = cloud_spend[
        (cloud_spend["year_month"] >= period_start) &
        (cloud_spend["year_month"] <= period_end)
    ]

    spend = period_spend["spend"]
    actual_cost_to_date = spend.sum()

    last_spend_month = period_spend["year_month"].max()
    months_remaining = (
        (period_end.year - last_spend_month.year) * 12
        + (period_end.month - last_spend_month.month)
    )

    
    suggestion = suggest_method(
        spend,
        has_project_estimations=len(project_adjustments) > 0,
        expected_monthly_spend=expected_monthly_spend
    )

    if selected_method is None:
        method = suggestion["suggested_method"]
    else:
        method = selected_method

    
    if method == "historic_growth_forecast":
        forecast_result = historic_growth_forecast(spend, months_remaining)

    elif method == "moving_average_forecast":
        forecast_result = moving_average_forecast(spend, months_remaining)

    elif method == "run_rate_forecast":
        forecast_result = run_rate_forecast(spend, months_remaining)

    elif method == "monthly_expectation_based_forecast":
        forecast_result = monthly_expectation_based_forecast(expected_monthly_spend, months_remaining)

    elif method == "project_expectation_forecast":
        base_forecast_result = run_rate_forecast(spend, months_remaining)
        forecast_result = project_expectation_forecast(base_forecast_result, project_adjustments)

    elif method == "single_exponential_smoothing_forecast":
        forecast_result = single_exponential_smoothing_forecast(spend, months_remaining)

    elif method == "holt_double_exponential_smoothing_forecast":
        forecast_result = holt_double_exponential_smoothing_forecast(spend, months_remaining)

    elif method == "holtwinters_triple_exponential_smoothing_forecast":
        forecast_result = holtwinters_triple_exponential_smoothing_forecast(spend, months_remaining)

    else:
        return {
            "cloud": cloud,
            "status": "Insufficient data",
            "message": "No historical spend, project adjustment, or manual assumption available.",
            "suggestion": suggestion
        }

    if forecast_result is None:
        return {
            "cloud": cloud,
            "status": "Forecast failed",
            "message": f"{method} could not produce a forecast for the available data.",
            "suggestion": suggestion
        }
    
    gap_analysis = forecast_gap(
        actual_cost_to_date=actual_cost_to_date,
        future_spend_total=forecast_result["future_spend_total"],
        commitment=commitment
    )

    required_growth = required_growth_rate(
        current_monthly_spend=spend.iloc[-1],
        actual_cost_to_date=actual_cost_to_date,
        commitment=commitment,
        months_remaining=months_remaining
    )

    return {
        "cloud": cloud,
        "method_used": method,
        "period_start": period_start.strftime("%Y-%m"),
        "period_end": period_end.strftime("%Y-%m"),
        "months_remaining": months_remaining,
        "required_monthly_growth_rate (%)": required_growth,
        "monthly_forecasts": forecast_result["monthly_forecasts"],
        **gap_analysis      }


def compare_statistical_methods(spend_data, commitments, cloud):
    
    spend_data = spend_data_validation(spend_data)
    commitments = commitment_data_validation(commitments)

    cloud_spend = spend_data[spend_data["cloud"] == cloud]
    cloud_commitment = commitments[commitments["cloud"] == cloud].iloc[0]

    period_start = cloud_commitment["period_start"]
    period_end = cloud_commitment["period_end"]
    commitment = cloud_commitment["commitment"]

    period_spend = cloud_spend[
        (cloud_spend["year_month"] >= period_start) &
        (cloud_spend["year_month"] <= period_end)
    ]

    spend = period_spend["spend"]
    actual_cost_to_date = spend.sum()

    last_spend_month = period_spend["year_month"].max()
    months_remaining = (
        (period_end.year - last_spend_month.year) * 12
        + (period_end.month - last_spend_month.month)
    )
    
    statistical_methods = {
        "run_rate": run_rate_forecast,
        "moving_average": moving_average_forecast,
        "historic_growth": historic_growth_forecast,
        "single_exponential_smoothing": single_exponential_smoothing_forecast,
        "holt_double_exponential_smoothing": holt_double_exponential_smoothing_forecast,
        "holtwinters_triple_exponential_smoothing": holtwinters_triple_exponential_smoothing_forecast
    }
    comparison = []

    for method_name, forecast_function in statistical_methods.items():

        forecast_result = forecast_function(spend, months_remaining)

        if forecast_result is None:
            continue

        gap_result = forecast_gap(
            actual_cost_to_date=actual_cost_to_date,
            future_spend_total=forecast_result["future_spend_total"],
            commitment=commitment
        )

        comparison.append({
            "cloud": cloud,
            "method": method_name,
            "months_remaining": months_remaining,
            "actual_cost_to_date": actual_cost_to_date,
            "future_spend_total": forecast_result["future_spend_total"],
            "forecasted_total_spend": gap_result["forecasted_total_spend"],
            "commitment": commitment,
            "gap": gap_result["gap"],
            "status": gap_result["status"]
        })

    return pd.DataFrame(comparison)
