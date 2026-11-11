from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

DATA_PATH = Path(__file__).resolve().with_name("weather_silver.csv")
OUTPUT_PATH = Path(__file__).resolve().with_name("weather_forecast.csv")
MIN_OBSERVATIONS = 60
FEATURES = ["lag_1", "lag_2", "lag_3", "lag_7", "rolling_mean_7"]


def build_features(city_data):
    data = city_data.sort_values("event_timestamp").copy()
    data["lag_1"] = data["temperature"].shift(1)
    data["lag_2"] = data["temperature"].shift(2)
    data["lag_3"] = data["temperature"].shift(3)
    data["lag_7"] = data["temperature"].shift(7)
    data["rolling_mean_7"] = data["temperature"].shift(1).rolling(7).mean()
    return data.dropna(subset=FEATURES + ["temperature"])


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Historique Silver introuvable : {DATA_PATH}")
    observations = pd.read_csv(DATA_PATH, parse_dates=["event_timestamp"])
    required = {"city", "temperature", "event_timestamp"}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(missing))}")

    forecasts = []
    for city, city_data in observations.groupby("city"):
        city_data = city_data.sort_values("event_timestamp").drop_duplicates(
            "event_timestamp", keep="last"
        )
        if len(city_data) < MIN_OBSERVATIONS:
            print(
                f"SKIP {city}: {len(city_data)}/{MIN_OBSERVATIONS} observations; "
                "collecte quotidienne nécessaire avant l'entraînement."
            )
            continue

        cadence_hours = city_data["event_timestamp"].diff().dt.total_seconds().dropna() / 3600
        median_cadence = cadence_hours.median()
        if not 18 <= median_cadence <= 30:
            print(f"SKIP {city}: cadence médiane {median_cadence:.1f} h, environ 24 h attendues.")
            continue

        dataset = build_features(city_data)
        split_at = int(len(dataset) * 0.8)
        if split_at < 30 or len(dataset) - split_at < 10:
            print(f"SKIP {city}: pas assez d'exemples pour une validation temporelle.")
            continue

        train = dataset.iloc[:split_at]
        validation = dataset.iloc[split_at:]
        model = RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(train[FEATURES], train["temperature"])
        model_predictions = model.predict(validation[FEATURES])
        baseline_predictions = validation["lag_1"].to_numpy()
        model_mae = mean_absolute_error(validation["temperature"], model_predictions)
        baseline_mae = mean_absolute_error(validation["temperature"], baseline_predictions)
        selected_model = "RandomForest" if model_mae < baseline_mae else "Persistence"

        latest_features = build_features(city_data).iloc[-1:][FEATURES]
        if selected_model == "RandomForest":
            model.fit(dataset[FEATURES], dataset["temperature"])
            next_temperature = float(model.predict(latest_features)[0])
        else:
            next_temperature = float(latest_features["lag_1"].iloc[0])

        forecasts.append({
            "city": city,
            "forecast_for": (
                city_data["event_timestamp"].max() + pd.Timedelta(hours=24)
            ).isoformat(),
            "forecast_temperature": round(next_temperature, 1),
            "selected_model": selected_model,
            "validation_mae": round(model_mae, 3),
            "persistence_baseline_mae": round(baseline_mae, 3),
            "validation_rmse": round(
                mean_squared_error(validation["temperature"], model_predictions) ** 0.5,
                3,
            ),
            "validation_observations": len(validation),
        })

    if not forecasts:
        raise SystemExit(
            "Aucune prévision produite : il faut au moins 60 observations quotidiennes "
            "par ville avec une cadence régulière."
        )
    pd.DataFrame(forecasts).to_csv(OUTPUT_PATH, index=False)
    print(f"Prévisions évaluées enregistrées dans {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
