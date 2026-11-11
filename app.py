from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from weather_metrics import add_weather_scores

ROOT = Path(__file__).resolve().parent
SILVER_PATH = ROOT / "weather_silver.csv"
FORECAST_PATH = ROOT / "weather_forecast.csv"

st.set_page_config(page_title="Météo Maroc | Analyse", page_icon="🌤️", layout="wide")
st.title("Météo au Maroc — aide à la décision")
st.caption("Analyse comparative des conditions observées dans les villes suivies.")

if not SILVER_PATH.exists():
    st.error("Fichier météo introuvable. Lancez d’abord le pipeline ou ajoutez weather_silver.csv.")
    st.stop()

observations = pd.read_csv(SILVER_PATH)
required = {"city", "temperature", "humidity", "wind_speed", "weather_main", "event_timestamp"}
missing = required.difference(observations.columns)
if missing:
    st.error(f"Colonnes manquantes dans weather_silver.csv : {', '.join(sorted(missing))}")
    st.stop()
if observations.empty:
    st.error("Le fichier météo ne contient aucune observation.")
    st.stop()

observations["event_timestamp"] = pd.to_datetime(observations["event_timestamp"], errors="coerce")
observations = observations.dropna(subset=["event_timestamp"])
if observations.empty:
    st.error("Aucun horodatage valide dans weather_silver.csv.")
    st.stop()

observations = add_weather_scores(observations)

city_options = sorted(observations["city"].dropna().unique())
selected_cities = st.multiselect("Villes à comparer", city_options, default=city_options)
if not selected_cities:
    st.info("Sélectionnez au moins une ville.")
    st.stop()

minimum_date = observations["event_timestamp"].min().date()
maximum_date = observations["event_timestamp"].max().date()
date_range = st.date_input(
    "Période d'analyse",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

observations = observations[
    observations["event_timestamp"].dt.date.between(start_date, end_date)
]
observations = add_weather_scores(observations)
latest_time = observations["event_timestamp"].max()
if pd.isna(latest_time):
    st.info("Aucune observation pour la période choisie.")
    st.stop()
age_hours = (pd.Timestamp.now() - latest_time).total_seconds() / 3600
if age_hours > 48:
    st.warning(f"Données potentiellement périmées : dernière observation le {latest_time:%d/%m/%Y à %H:%M}.")
else:
    st.success(f"Dernière observation : {latest_time:%d/%m/%Y à %H:%M}.")

con = duckdb.connect(":memory:")
con.register("weather_observations", observations)
latest = con.execute(
    """
    SELECT * EXCLUDE (row_number)
    FROM (
        SELECT *, row_number() OVER (
            PARTITION BY city ORDER BY event_timestamp DESC
        ) AS row_number
        FROM weather_observations
        WHERE city IN (SELECT unnest(?))
    )
    WHERE row_number = 1
    ORDER BY weather_score DESC, city
    """,
    [selected_cities],
).df()

if latest.empty:
    st.info("Aucune observation disponible pour les villes sélectionnées.")
    st.stop()

filtered = observations[observations["city"].isin(selected_cities)]
average_scores = (
    filtered.groupby("city", as_index=False)["weather_score"]
    .mean()
    .sort_values("weather_score", ascending=False)
)
first, second, third = st.columns(3)
first.metric("Villes comparées", len(latest))
second.metric("Température moyenne (période)", f"{filtered['temperature'].mean():.1f} °C")
third.metric("Meilleur score moyen", f"{average_scores['weather_score'].max():.1f}/100")

st.subheader("Classement — dernière observation de la période")
ranking = latest[[
    "city", "temperature", "humidity", "wind_speed",
    "weather_main", "weather_score", "recommendation",
]].rename(columns={
    "city": "Ville",
    "temperature": "Température (°C)",
    "humidity": "Humidité (%)",
    "wind_speed": "Vent (m/s)",
    "weather_main": "Conditions",
    "weather_score": "Score / 100",
    "recommendation": "Recommandation",
})
st.dataframe(ranking, hide_index=True, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Évolution de la température")
    temperature_chart = px.line(
        filtered.sort_values("event_timestamp"),
        x="event_timestamp",
        y="temperature",
        color="city",
        markers=True,
        labels={"event_timestamp": "Date", "temperature": "Température (°C)", "city": "Ville"},
    )
    st.plotly_chart(temperature_chart, use_container_width=True)
with right:
    st.subheader("Score moyen sur la période")
    score_chart = px.bar(
        average_scores.sort_values("weather_score", ascending=True),
        x="weather_score",
        y="city",
        orientation="h",
        range_x=[0, 100],
        labels={"weather_score": "Score moyen / 100", "city": "Ville"},
    )
    st.plotly_chart(score_chart, use_container_width=True)

st.caption(
    "Le score est un indicateur explicable basé sur la température, l'humidité, "
    "le vent et le type de ciel; il ne remplace pas une prévision météo officielle."
)

st.download_button(
    "Télécharger les observations filtrées (CSV)",
    filtered.to_csv(index=False).encode("utf-8"),
    file_name="observations_meteo.csv",
    mime="text/csv",
)

if FORECAST_PATH.exists():
    st.subheader("Prévisions expérimentales")
    forecast = pd.read_csv(FORECAST_PATH)
    forecast = forecast[forecast["city"].isin(selected_cities)]
    if forecast.empty:
        st.info("Aucune prévision disponible pour les villes sélectionnées.")
    else:
        st.caption(
            "Prévision de la prochaine observation, évaluée hors échantillon et "
            "comparée à une baseline de persistance."
        )
        st.dataframe(forecast, hide_index=True, use_container_width=True)
else:
    st.info(
        "Aucune prévision disponible. Collectez au moins 60 observations quotidiennes "
        "par ville, puis lancez `python forecast.py`."
    )
