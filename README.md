# Météo Maroc — plateforme analytique

Projet portfolio de bout en bout centré sur une question métier : **quelle ville offre les meilleures conditions météo pour une sortie aujourd'hui, et comment ces conditions évoluent-elles ?**

## Ce que le projet démontre

- **Ingestion et orchestration** : API OpenWeatherMap, stockage objet MinIO, pipeline Airflow planifié.
- **Modèle de données médaillon** : JSON Bronze, historique nettoyé Silver, classement Gold.
- **Analytique moderne** : transformations et tests dbt exécutés sur DuckDB.
- **Analyse métier** : tableau de bord Streamlit avec filtres, KPI, tendances, classement et export CSV.
- **Qualité et fiabilité** : contrôles bloquants dans Airflow, appels API avec timeout et erreurs HTTP visibles, ingestion répétable et historisation.
- **Expérimentation prédictive** : script de prévision de température par Random Forest, comparé à une baseline de persistance sur une validation temporelle.

## Architecture

```text
OpenWeatherMap
      |
      v
MinIO Bronze (réponses JSON) --> Silver (historique CSV nettoyé)
                                      |                  |
                                      v                  v
                              MinIO Gold (score)     DuckDB + dbt
                                      |                  |
                                      +------> Streamlit dashboard
                                      |
                                      +------> export CSV / Power BI
```

Le score de confort est une règle métier transparente, pas un modèle d'IA : température (40 points), humidité (30), vent (20) et ciel dégagé/nuageux (10). Le score est un indicateur pédagogique et ne constitue pas un conseil météo officiel.

## Prérequis

- Python 3.10+
- MinIO avec les buckets `bronze`, `silver` et `gold`
- Airflow/Docker uniquement pour l'orchestration planifiée
- Une clé OpenWeatherMap pour la collecte en direct

## Installation locale (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Ajoutez votre clé dans `.env` (`OPENWEATHER_API_KEY`) et définissez un mot de passe Airflow local robuste (`AIRFLOW_ADMIN_PASSWORD`). Vérifiez que MinIO est démarré. Les identifiants MinIO par défaut dans l'exemple sont réservés au développement local : changez-les pour tout déploiement.

Avant de publier le dépôt, révoquez et remplacez la clé OpenWeatherMap de l'ancienne version : elle était auparavant codée en dur dans le script d'ingestion.

Exécutez les étapes dans l'ordre :

```powershell
python ingest_weather.py
python transform_silver.py
python transform_gold.py
python quality_checks.py
```

L'ingestion ajoute des instantanés au Bronze. Silver relit l'historique Bronze, déduplique avec la clé `city + event_timestamp` et actualise `weather_silver.csv`; Gold classe la dernière observation disponible de chaque ville. Les scripts exportent aussi des copies locales pour l'analyse.

Les contrôles qualité retournent un code d'échec si une vérification échoue. Il faut donc corriger le DAG en échec avant de considérer une exécution comme réussie.

## Tableau de bord

```powershell
streamlit run app.py
```

Le tableau de bord utilise DuckDB pour sélectionner la dernière observation par ville et Streamlit/Plotly pour afficher les KPI, le classement, les recommandations et les tendances. Il permet de filtrer villes et dates, signale les données de plus de 48 heures comme potentiellement périmées, et expose les prévisions évaluées si elles existent. Pour exporter les derniers fichiers depuis MinIO vers le dossier du projet, lancez `python export_for_powerbi.py`; Power BI peut ensuite se connecter à `weather_silver.csv` et `weather_gold.csv`.

## Modélisation dbt + DuckDB

Depuis la racine du projet, après avoir produit `weather_silver.csv` :

```powershell
dbt build --project-dir dbt --profiles-dir dbt
```

Le modèle `stg_weather` type les champs, `mart_city_weather` conserve la dernière observation de chaque ville par jour et calcule le score/rang. Les tests dbt vérifient les colonnes, l'unicité des observations et les bornes du score. Le fichier DuckDB généré est local et ignoré par Git.

## Prévision (expérimentation)

```powershell
python forecast.py
```

Le modèle ne s'entraîne que si chaque ville a au moins 60 observations, avec une cadence médiane de 18 à 30 heures. La séparation train/validation respecte l'ordre temporel. Le script compare le Random Forest à la baseline « prochaine température = dernière température » et rapporte MAE/RMSE; il retient la baseline si le modèle ne fait pas mieux. Avec le petit CSV d'exemple (quelques lignes), le script s'arrête explicitement : il faut collecter environ deux mois de données quotidiennes avant de prétendre à une prévision crédible.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Limites connues et pistes d'évolution

- L'API gratuite fournit des conditions actuelles, pas un historique météo complet; la collecte quotidienne construit cet historique à partir de maintenant.
- Le classement compare les dernières observations disponibles et ne tient pas encore compte des préférences individuelles.
- Une seule observation par jour ne permet pas d'étudier les variations intrajournalières. Une fréquence plus élevée et des données de précipitations/ressenti enrichiraient l'analyse.
- Pour la production : secrets dans un gestionnaire dédié, stockage transactionnel, alertes, tests de contrats API, CI, suivi de fraîcheur et validation du modèle dans le temps.
