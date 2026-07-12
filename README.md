# Overcast

Cloud Cost Commitment Forecasting Tool

## Overview

This application forecasts future public cloud spend using historical monthly cloud spend data and compares the forecast against contracted cloud commitments. It supports multiple cloud providers and recommends an appropriate statistical forecasting method based on characteristics of the historical spend data.

For each cloud provider, the tool:

- Forecasts future monthly spend until the end of the commitment period.
- Calculates the total forecasted spend.
- Determines whether the contracted commitment is expected to be met.
- Calculates the forecast gap.
- Calculates the monthly growth rate required to meet the commitment if the forecast falls short.
- Generates visualisations and a downloadable JSON report.

---

## Features

- Upload historical cloud spend data.
- Upload cloud commitment data.
- Support for multiple cloud providers.
- Automatic forecasting method recommendation.
- Manual forecasting method selection.
- Statistical forecasting methods:
  - Run Rate
  - Moving Average
  - Historic Growth
  - Single Exponential Smoothing (SES)
  - Holt Double Exponential Smoothing
  - Holt-Winters Triple Exponential Smoothing
- Optional planned project adjustments.
- Commitment gap analysis.
- Required monthly growth rate calculation.
- Monthly spend forecast visualisation.
- Cumulative spend versus commitment visualisation.
- Save and load forecast reports.

---

## Forecasting Methodology

Before generating a forecast, the application analyses the historical spend data and recommends an appropriate forecasting method.

The recommendation is based on several diagnostics including:

- Number of historical observations
- Trend detection
- Spend stability
- Month-to-month volatility
- Recent growth level-off
- Optional user indication of seasonality

### Run Rate

**Suggested when:** fewer than three months of historical data are available.

Uses the average historical monthly spend as the future monthly forecast when insufficient data exists to identify meaningful patterns.

### Moving Average

**Suggested when:** spend is volatile or no clear data pattern is detected.

Smooths short-term fluctuations by averaging recent observations.

### Historic Growth

Available as an optional forecasting method.

Forecasts future spend using the compound monthly growth rate observed between the first and last historical observations.

### Single Exponential Smoothing (SES)

**Suggested when:** spend is stable or historical growth has recently levelled off.

Models a stable underlying spending level while smoothing random fluctuations.

### Holt Double Exponential Smoothing

**Suggested when:** a clear trend exists without excessive volatility.

Models both the current spending level and a persistent trend.

### Holt-Winters Triple Exponential Smoothing

**Available when:** seasonal forecasting is enabled and at least 24 months of historical data are available.

Models level, trend and repeating seasonal patterns.

---

## Method Recommendation Criteria

The forecasting recommendation engine evaluates several characteristics of the historical spend data.

| Diagnostic | Purpose |
|------------|---------|
| Number of observations | Determines whether sufficient history exists for statistical forecasting. |
| Relative trend | Detects consistent increases or decreases in cloud spend. |
| Coefficient of variation | Measures overall spend stability. |
| Month-to-month volatility | Detects irregular fluctuations that may reduce forecast reliability. |
| Recent level-off | Detects whether earlier growth has stabilised, favouring level-based forecasting. |
| Optional seasonality | Allows Holt-Winters forecasting when recurring seasonal behaviour is expected and sufficient historical data exists. |

The suggested forecasting method is selected according to the assumptions that best match the historical data.

---

## Forecast Outputs

For each cloud provider, the generated report includes:

- Forecasting method used
- Forecasted monthly spend
- Forecasted total spend
- Actual spend to date
- Contracted commitment
- Forecast gap
- Forecast status
- Required monthly growth rate
- Historical and forecast spend plot
- Cumulative spend versus commitment plot

Reports can be downloaded and reloaded as JSON files.

---

## Required Input Files

### Spend Data

CSV with the following columns:

| Column | Description |
|--------|-------------|
| `cloud` | Cloud provider name |
| `year_month` | Month in `YYYY-MM` format |
| `spend` | Historical monthly spend |

Example:

```csv
cloud,year_month,spend
AWS,2025-01,12000
AWS,2025-02,12500
```

---

### Commitment Data

CSV with the following columns:

| Column | Description |
|--------|-------------|
| `cloud` | Cloud provider name |
| `period_start` | Commitment start month (`YYYY-MM`) |
| `period_end` | Commitment end month (`YYYY-MM`) |
| `commitment` | Total contracted spend |

Example:

```csv
cloud,period_start,period_end,commitment
AWS,2025-01,2025-12,180000
```

---

## Assumptions

- Each cloud provider has a single commitment period.
- Historical spend values represent monthly totals.
- Spend and commitment values use the same currency.
- The tool performs no currency conversion.
- Holt-Winters forecasting requires at least 24 months of historical data.

---

## Repository Contents

| File | Description |
|------|-------------|
| `app.py` | Streamlit user interface |
| `forecasting.py` | Statistical forecasting models |
| `reporting.py` | Forecast generation, diagnostics and reporting logic |
| `validation.py` | Input validation functions |
| `requirements.txt` | Python package dependencies |
| `test files/` | Synthetic datasets used for testing |
| `README.md` | Project documentation |

---

## Dependencies

The application requires the following Python packages:

- streamlit
- pandas
- numpy
- matplotlib
- statsmodels
