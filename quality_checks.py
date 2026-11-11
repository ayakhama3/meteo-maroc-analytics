import json
import pandas as pd
import sys

from weather_config import iter_objects, s3_client

s3 = s3_client()

errors = []
passed = 0

def check(name, condition, message):
    global passed
    if condition:
        print(f"  OK  {name}")
        passed += 1
    else:
        print(f"  FAIL {name} --> {message}")
        errors.append(f"{name}: {message}")

# =====================================================
# TEST 1 : BRONZE - Les fichiers existent
# =====================================================
print("\n=== TEST 1 : BRONZE - Fichiers JSON ===")
bronze_files = [obj["Key"] for obj in iter_objects(s3, "bronze", "weather_raw/")
                if obj["Key"].endswith(".json")]

check("Fichiers Bronze existent",
      len(bronze_files) > 0,
      "Aucun fichier JSON trouve dans bronze/weather_raw/")

check("4 villes dans Bronze",
      len(bronze_files) >= 4,
      f"Seulement {len(bronze_files)} fichiers trouves, 4 attendus")

# Verifier le contenu de chaque fichier
bronze_cities = set()
for key in bronze_files:
    file_obj = s3.get_object(Bucket="bronze", Key=key)
    data = json.loads(file_obj["Body"].read().decode("utf-8"))
    if data.get("name"):
        bronze_cities.add(data["name"])

    check(f"Champ 'name' present dans {key.split('/')[-1]}",
          "name" in data,
          "Champ name manquant")

    check(f"Temperature valide pour {data.get('name', '?')}",
          -10 <= data.get("main", {}).get("temp", 999) <= 60,
          f"Temperature anormale : {data.get('main', {}).get('temp')}")

    check(f"Humidite valide pour {data.get('name', '?')}",
          0 <= data.get("main", {}).get("humidity", -1) <= 100,
          f"Humidite anormale : {data.get('main', {}).get('humidity')}")

check("4 villes distinctes dans Bronze",
      len(bronze_cities) >= 4,
      f"Seulement {len(bronze_cities)} villes distinctes")

# =====================================================
# TEST 2 : SILVER - Types et valeurs
# =====================================================
print("\n=== TEST 2 : SILVER - Types et valeurs ===")
silver_files = [obj["Key"] for obj in iter_objects(s3, "silver", "weather_clean/")
                if obj["Key"].endswith(".csv")]

check("Fichiers Silver existent",
      len(silver_files) > 0,
      "Aucun fichier CSV trouve dans silver/weather_clean/")

if silver_files:
    latest = sorted(silver_files)[-1]
    file_obj = s3.get_object(Bucket="silver", Key=latest)
    df_silver = pd.read_csv(file_obj["Body"])

    check("Colonnes requises presentes",
          all(col in df_silver.columns for col in
              ["city", "temperature", "humidity",
               "wind_speed", "event_timestamp",
               "ingestion_timestamp"]),
          "Colonnes manquantes dans Silver")

    check("Pas de valeurs nulles",
          df_silver.isnull().sum().sum() == 0,
          f"{df_silver.isnull().sum().sum()} valeurs nulles trouvees")

    check("Temperature entre -10 et 60",
          df_silver["temperature"].between(-10, 60).all(),
          "Valeurs de temperature hors limites")

    check("Humidite entre 0 et 100",
          df_silver["humidity"].between(0, 100).all(),
          "Valeurs d'humidite hors limites")

    check("4 villes dans Silver",
          df_silver["city"].nunique() >= 4,
          f"Seulement {df_silver['city'].nunique()} villes")
    check("Clé ville/date unique",
          not df_silver.duplicated(["city", "event_timestamp"]).any(),
          "Observations dupliquées pour une ville et un horodatage")

# =====================================================
# TEST 3 : GOLD - KPI
# =====================================================
print("\n=== TEST 3 : GOLD - KPI et scores ===")
gold_files = [obj["Key"] for obj in iter_objects(s3, "gold", "weather_analytics/")
              if obj["Key"].endswith(".csv")]

check("Fichiers Gold existent",
      len(gold_files) > 0,
      "Aucun fichier CSV trouve dans gold/weather_analytics/")

if gold_files:
    latest = sorted(gold_files)[-1]
    file_obj = s3.get_object(Bucket="gold", Key=latest)
    df_gold = pd.read_csv(file_obj["Body"])

    check("Colonne weather_score presente",
          "weather_score" in df_gold.columns,
          "Colonne weather_score manquante")

    check("Colonne rank presente",
          "rank" in df_gold.columns,
          "Colonne rank manquante")

    check("Scores entre 0 et 100",
          df_gold["weather_score"].between(0, 100).all(),
          "Scores hors limites")

    check("Une meilleure ville identifiee",
          df_gold["rank"].min() == 1,
          "Aucune ville classee 1")

# =====================================================
# RAPPORT FINAL
# =====================================================
total = passed + len(errors)
print(f"\n{'='*40}")
print(f"RAPPORT QUALITE : {passed}/{total} tests passes")
if errors:
    print(f"ECHECS ({len(errors)}) :")
    for e in errors:
        print(f"  - {e}")
else:
    print("Tous les tests sont passes avec succes !")
print(f"{'='*40}")
if errors:
    sys.exit(1)