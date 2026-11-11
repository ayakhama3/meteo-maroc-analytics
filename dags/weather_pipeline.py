from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import sys

# =====================================================
# CONFIGURATION DU DAG
# =====================================================
default_args = {
    "owner": "emsi",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

dag = DAG(
    dag_id="weather_pipeline",
    default_args=default_args,
    description="Pipeline meteo complet : Bronze -> Silver -> Gold -> Qualite",
    schedule_interval="0 6 * * *",  # Tous les jours a 6h du matin
    start_date=datetime(2026, 4, 18),
    catchup=False,
    tags=["meteo", "emsi", "data-pipeline"],
)

# =====================================================
# FONCTIONS DES TACHES
# =====================================================
def run_ingestion():
    print("Lancement de l'ingestion Bronze...")
    result = subprocess.run(
        [sys.executable, "/opt/airflow/scripts/ingest_weather.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Erreur ingestion : {result.stderr}")
    print("Ingestion Bronze terminee !")

def run_silver():
    print("Lancement de la transformation Silver...")
    result = subprocess.run(
        [sys.executable, "/opt/airflow/scripts/transform_silver.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Erreur Silver : {result.stderr}")
    print("Transformation Silver terminee !")

def run_gold():
    print("Lancement de la transformation Gold...")
    result = subprocess.run(
        [sys.executable, "/opt/airflow/scripts/transform_gold.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Erreur Gold : {result.stderr}")
    print("Transformation Gold terminee !")

def run_quality():
    print("Lancement des tests qualite...")
    result = subprocess.run(
        [sys.executable, "/opt/airflow/scripts/quality_checks.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Erreur Qualite : {result.stderr}")
    print("Tests qualite termines !")

# =====================================================
# DEFINITION DES TACHES
# =====================================================
task_ingestion = PythonOperator(
    task_id="ingestion_bronze",
    python_callable=run_ingestion,
    dag=dag,
)

task_silver = PythonOperator(
    task_id="transformation_silver",
    python_callable=run_silver,
    dag=dag,
)

task_gold = PythonOperator(
    task_id="transformation_gold",
    python_callable=run_gold,
    dag=dag,
)

task_quality = PythonOperator(
    task_id="qualite_donnees",
    python_callable=run_quality,
    dag=dag,
)

# =====================================================
# ORDRE D'EXECUTION
# =====================================================
task_ingestion >> task_silver >> task_gold >> task_quality