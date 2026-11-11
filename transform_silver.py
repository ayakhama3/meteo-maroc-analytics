import json
import pandas as pd
from datetime import datetime
from io import StringIO
from pathlib import Path

from weather_config import iter_objects, s3_client

BUCKET_BRONZE    = "bronze"
BUCKET_SILVER    = "silver"
s3 = s3_client()

# =====================================================
# LISTER LES FICHIERS DANS BRONZE
# =====================================================
print("Lecture des fichiers Bronze...")
records = []

for obj in iter_objects(s3, BUCKET_BRONZE, "weather_raw/"):
    key = obj["Key"]
    if not key.endswith(".json"):
        continue

    # Lire le fichier JSON
    file_obj = s3.get_object(Bucket=BUCKET_BRONZE, Key=key)
    data = json.loads(file_obj["Body"].read().decode("utf-8"))

    # =====================================================
    # EXTRACTION DES CHAMPS UTILES
    # =====================================================
    record = {
        "city":                data.get("name", ""),
        "country":             data.get("sys", {}).get("country", ""),
        "latitude":            float(data.get("coord", {}).get("lat", 0)),
        "longitude":           float(data.get("coord", {}).get("lon", 0)),
        "temperature":         float(data.get("main", {}).get("temp", 0)),
        "temp_min":            float(data.get("main", {}).get("temp_min", 0)),
        "temp_max":            float(data.get("main", {}).get("temp_max", 0)),
        "feels_like":          float(data.get("main", {}).get("feels_like", 0)),
        "humidity":            int(data.get("main", {}).get("humidity", 0)),
        "pressure":            int(data.get("main", {}).get("pressure", 0)),
        "weather_main":        data.get("weather", [{}])[0].get("main", ""),
        "weather_description": data.get("weather", [{}])[0].get("description", ""),
        "wind_speed":          float(data.get("wind", {}).get("speed", 0)),
        "wind_deg":            int(data.get("wind", {}).get("deg", 0)),
        "event_timestamp":     datetime.utcfromtimestamp(
                                   data.get("dt", 0)
                               ).strftime("%Y-%m-%d %H:%M:%S"),
        "ingestion_timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }

    records.append(record)
    print(f"OK Traite : {record['city']}")

# =====================================================
# NETTOYAGE DES DONNEES
# =====================================================
df = pd.DataFrame(records)
if df.empty:
    raise RuntimeError("Aucune observation météo trouvée dans la couche Bronze.")

# La lecture de tout Bronze reconstruit un historique cumulatif et idempotent.
df = df.drop_duplicates(subset=["city", "event_timestamp"])
df = df.dropna()
df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], errors="coerce")
df["ingestion_timestamp"] = pd.to_datetime(df["ingestion_timestamp"], errors="coerce")
df = df.dropna(subset=["event_timestamp", "ingestion_timestamp"])
df = df.sort_values(["event_timestamp", "city"]).reset_index(drop=True)
if df.empty:
    raise RuntimeError("Aucune observation valide après nettoyage.")

# =====================================================
# SAUVEGARDE DANS SILVER
# =====================================================
now = datetime.now()
date_str = now.strftime("%Y-%m-%d")
time_str = now.strftime("%Hh%M%S")

csv_buffer = StringIO()
df.to_csv(csv_buffer, index=False)

path = f"weather_clean/date={date_str}/data_{time_str}.csv"

s3.put_object(
    Bucket=BUCKET_SILVER,
    Key=path,
    Body=csv_buffer.getvalue(),
    ContentType="text/csv"
)

df.to_csv(Path(__file__).with_name("weather_silver.csv"), index=False)
print(f"\nOK Silver Layer sauvegarde : silver/{path}")
print(f"OK {len(df)} observations historiques pour {df['city'].nunique()} villes.")