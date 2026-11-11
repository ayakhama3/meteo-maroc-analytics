import pandas as pd
from datetime import datetime
from io import StringIO
from pathlib import Path

from weather_config import iter_objects, s3_client
from weather_metrics import add_weather_scores

BUCKET_SILVER    = "silver"
BUCKET_GOLD      = "gold"
s3 = s3_client()

# =====================================================
# LIRE LE FICHIER CSV DEPUIS SILVER
# =====================================================
print("Lecture des donnees Silver...")
files = sorted(
    obj["Key"] for obj in iter_objects(s3, BUCKET_SILVER, "weather_clean/")
    if obj["Key"].endswith(".csv")
)
if not files:
    raise RuntimeError("Aucun CSV Silver trouvé.")
latest_file = files[-1]

file_obj = s3.get_object(Bucket=BUCKET_SILVER, Key=latest_file)
df = pd.read_csv(file_obj["Body"])
if df.empty:
    raise RuntimeError("Le fichier Silver est vide.")
print(f"OK {len(df)} observations lues depuis Silver")

df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], errors="coerce")
df = df.dropna(subset=["event_timestamp"])
df = df.sort_values("event_timestamp").drop_duplicates("city", keep="last")
df = add_weather_scores(df)
df = df.sort_values(["weather_score", "city"], ascending=[False, True]).reset_index(drop=True)
df["rank"] = range(1, len(df) + 1)
df["date"] = datetime.now().strftime("%Y-%m-%d")

print("\n===== CLASSEMENT DES VILLES =====")
for _, row in df.iterrows():
    print(f"{int(row['rank'])}. {row['city']:12} | "
          f"Score: {row['weather_score']}/100 | "
          f"Temp: {row['temperature']}C | "
          f"Meteo: {row['weather_main']:10} | "
          f"{row['recommendation']}")

meilleure_ville = df.iloc[0]["city"]
print(f"\nMeilleure destination : {meilleure_ville} !")

# =====================================================
# SAUVEGARDE DANS GOLD
# =====================================================
now = datetime.now()
date_str = now.strftime("%Y-%m-%d")
time_str = now.strftime("%Hh%M%S")

csv_buffer = StringIO()
df.to_csv(csv_buffer, index=False)

path = f"weather_analytics/date={date_str}/data_{time_str}.csv"

s3.put_object(
    Bucket=BUCKET_GOLD,
    Key=path,
    Body=csv_buffer.getvalue(),
    ContentType="text/csv"
)

df.to_csv(Path(__file__).with_name("weather_gold.csv"), index=False)
print(f"\nOK Gold Layer sauvegarde : gold/{path}")
print(f"OK Pipeline Gold termine avec succes !")