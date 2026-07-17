import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt, ExponentialSmoothing

################# Statistical Forecasting Methods #############################################

def moving_average_forecast(spend, months_remaining, window=3):
    if len(spend) == 0:
        return None

    # Convert pandas Series to list for efficient sequential appending
    spend_list = spend.tolist()
    monthly_forecasts = []

    for _ in range(months_remaining):
        current_window = spend_list[-window:] # selecting the last 'window' number of months from data
        next_month_forecast = sum(current_window) / len(current_window) # calculating the average of selected window
        monthly_forecasts.append(next_month_forecast) # store the forecasted spend
        spend_list.append(next_month_forecast) # append spend list so window moves a step foward next iteration

    future_spend_total = sum(monthly_forecasts)

    return {
        "method": "moving_average",
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": future_spend_total
    }


def run_rate_forecast(spend, months_remaining):
    if len(spend) == 0:
        return None

    monthly_forecast = spend.mean()
    monthly_forecasts = [monthly_forecast] * months_remaining
    future_spend_total = sum(monthly_forecasts)

    return {
        "method": "run_rate",
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": future_spend_total}


def historic_growth_forecast(spend, months_remaining):
    if len(spend) <= 1:
        return None

    first_spend = spend.iloc[0]
    last_spend = spend.iloc[-1]
    if first_spend <= 0:
        return None

    periods = len(spend) - 1
    growth_rate = (last_spend / first_spend) ** (1 / periods) - 1
    monthly_forecasts = []
    for i in range(1, months_remaining + 1):
        monthly_forecast = last_spend * ((1 + growth_rate) ** i)
        monthly_forecasts.append(monthly_forecast)
    
    future_spend_total = sum(monthly_forecasts)
    return {
        "method": "historic_growth",
        "growth_rate": growth_rate,
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": future_spend_total}


from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt, ExponentialSmoothing

def single_exponential_smoothing_forecast(spend, months_remaining): # Assumes no trend and no seasonality
    if len(spend) < 2:
        return None

    model = SimpleExpSmoothing(spend)
    fitted_model = model.fit(optimized=True)
    forecast = fitted_model.forecast(months_remaining)
    monthly_forecasts = forecast.tolist()

    return {
        "method": "single_exponential_smoothing",
        "alpha": fitted_model.model.params["smoothing_level"],
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": sum(monthly_forecasts)}


def holt_double_exponential_smoothing_forecast(spend, months_remaining): # Assumes trend present but no seasonality
    if len(spend) < 3:
        return None

    model = Holt(spend)
    fitted_model = model.fit(optimized=True)
    forecast = fitted_model.forecast(months_remaining)
    monthly_forecasts = forecast.tolist()

    return {
        "method": "holt_trend",
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": sum(monthly_forecasts),
        "smoothing_level": fitted_model.params["smoothing_level"],
        "smoothing_trend": fitted_model.params["smoothing_trend"] }


def holtwinters_triple_exponential_smoothing_forecast(spend, months_remaining, seasonal_periods=12): # Assumes both trend and seasonality present
    if len(spend) < 2*seasonal_periods: # Must have at least 2 years to check for seasonality across them
        return None

    model = ExponentialSmoothing(spend, trend="add", seasonal="add", seasonal_periods=seasonal_periods)
    fitted_model = model.fit(optimized=True)
    forecast = fitted_model.forecast(months_remaining)
    monthly_forecasts = forecast.tolist()

    return {
        "method": "holt_winters",
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": sum(monthly_forecasts),
        "smoothing_level": fitted_model.params["smoothing_level"],
        "smoothing_trend": fitted_model.params["smoothing_trend"],
        "smoothing_seasonal": fitted_model.params["smoothing_seasonal"]}


################## Business Information Forecasting Method #####################################################


def project_expectation_forecast(base_forecast_result, project_adjustments):
    
    monthly_forecasts = base_forecast_result["monthly_forecasts"].copy()
    for i in range(min(len(monthly_forecasts), len(project_adjustments))):
        monthly_forecasts[i] += project_adjustments[i]
   
    future_spend_total = sum(monthly_forecasts)
    return {
        "method": "project_adjusted",
        "monthly_forecasts": monthly_forecasts,
        "future_spend_total": future_spend_total   }

# To convert the forecast result dictionary from the above functions into a monthly forecast dataframe (useful for visualisations in Streamlit )

def forecast_result_to_df(forecast_result, last_spend_month, cloud=None):

    monthly_forecasts = forecast_result["monthly_forecasts"]

    future_months = pd.date_range(
        start=last_spend_month + pd.DateOffset(months=1),
        periods=len(monthly_forecasts),
        freq="MS"
    )

    forecast_df = pd.DataFrame({
        "year_month": future_months,
        "forecasted_spend": monthly_forecasts,
        "method": forecast_result["method"]
    })

    if cloud is not None:
        forecast_df["cloud"] = cloud

    return forecast_df
