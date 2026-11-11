import pandas as pd
from pathlib import Path

from weather_config import iter_objects, s3_client

s3 = s3_client()


def latest_csv(bucket, prefix):
    files = sorted(
        obj["Key"] for obj in iter_objects(s3, bucket, prefix)
        if obj["Key"].endswith(".csv")
    )
    if not files:
        raise RuntimeError(f"Aucun CSV trouvé dans {bucket}/{prefix}.")
    file_obj = s3.get_object(Bucket=bucket, Key=files[-1])
    return pd.read_csv(file_obj["Body"])

print("Lecture des donnees Gold...")
df_gold = latest_csv("gold", "weather_analytics/")

print("Lecture des donnees Silver...")
df_silver = latest_csv("silver", "weather_clean/")

root = Path(__file__).resolve().parent
df_gold.to_csv(root / "weather_gold.csv", index=False)
df_silver.to_csv(root / "weather_silver.csv", index=False)

print("OK weather_gold.csv sauvegarde !")
print("OK weather_silver.csv sauvegarde !")
print("\nContenu Gold :")
print(df_gold[["city", "temperature", "humidity",
               "wind_speed", "weather_score",
               "rank", "recommendation"]].to_string())