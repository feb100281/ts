# utils/forecast/model.py
from prophet import Prophet
import pandas as pd


def build_prophet_model(params: dict) -> Prophet:
    model = Prophet(
        yearly_seasonality=params["yearly_seasonality"],
        weekly_seasonality=params["weekly_seasonality"],
        daily_seasonality=params["daily_seasonality"],
        seasonality_mode=params["seasonality_mode"],
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        holidays_prior_scale=params["holidays_prior_scale"],
        interval_width=params["interval_width"],
    )

    if params.get("add_monthly_seasonality", False):
        model.add_seasonality(
            name="monthly",
            period=params.get("monthly_period", 30.5),
            fourier_order=params.get("monthly_fourier_order", 5),
        )

    return model


def make_forecast(data, end_date, forecast_date, prophet_params, freq="D"):
    end_date = pd.to_datetime(end_date)
    forecast_date = pd.to_datetime(forecast_date)

    periods = (forecast_date - end_date).days
    if periods < 0:
        raise ValueError("forecast_date должен быть позже или равен last_actual_date")

    model = build_prophet_model(prophet_params)
    model.fit(data)

    future = model.make_future_dataframe(periods=periods, freq=freq, include_history=True)
    forecast = model.predict(future)

    forecast["yhat"] = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

    return model, forecast

