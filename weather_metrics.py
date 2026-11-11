import pandas as pd


def calculate_weather_score(row):
    score = 0

    if 20 <= row["temperature"] <= 28:
        score += 40
    elif 15 <= row["temperature"] < 20 or 28 < row["temperature"] <= 32:
        score += 20
    else:
        score += 5

    if row["humidity"] < 40:
        score += 30
    elif row["humidity"] < 60:
        score += 20
    elif row["humidity"] < 80:
        score += 10

    if row["wind_speed"] < 3:
        score += 20
    elif row["wind_speed"] < 5:
        score += 15
    elif row["wind_speed"] < 8:
        score += 10

    if row["weather_main"] in ["Clear", "Sunny"]:
        score += 10
    elif row["weather_main"] == "Clouds":
        score += 5

    return score


def add_weather_scores(df):
    result = df.copy()
    result["weather_score"] = result.apply(calculate_weather_score, axis=1)
    result["recommendation"] = result["weather_score"].apply(
        lambda score: "Excellent" if score >= 80
        else "Bien" if score >= 60
        else "Moyen" if score >= 40
        else "Déconseillé"
    )
    return result
