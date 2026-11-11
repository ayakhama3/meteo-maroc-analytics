import json
import os
import requests
from datetime import datetime

from weather_config import s3_client

API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not API_KEY:
    raise RuntimeError("La variable OPENWEATHER_API_KEY doit être définie.")

CITIES = ["Marrakech", "Tanger", "Dakhla", "Essaouira"]
BUCKET_NAME = "bronze"

s3 = s3_client()

# Date et heure actuelles
now = datetime.now()
date_str = now.strftime("%Y-%m-%d")
time_str = now.strftime("%Hh%M%S")

# Collecter et stocker les données pour chaque ville
for city in CITIES:
    print(f"Collecte des données pour {city}...")

    # Appel API
    url = "https://api.openweathermap.org/data/2.5/weather"
    response = requests.get(
        url,
        params={"q": city, "appid": API_KEY, "units": "metric"},
        timeout=(5, 20),
    )
    response.raise_for_status()
    data = response.json()
    if "main" not in data or "dt" not in data:
        raise ValueError(f"Réponse météo invalide pour {city}.")

    # Chemin dans MinIO
    path = f"weather_raw/city={city}/date={date_str}/data_{time_str}.json"

    # Sauvegarde dans MinIO
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=path,
        Body=json.dumps(data, indent=2, ensure_ascii=False),
        ContentType="application/json"
    )

    print(f"✅ {city} sauvegardé dans MinIO : {path}")

print("\n✅ Ingestion terminée avec succès !")