import unittest

import pandas as pd

from weather_metrics import add_weather_scores, calculate_weather_score


class WeatherMetricsTests(unittest.TestCase):
    def test_ideal_conditions_score_one_hundred(self):
        row = {
            "temperature": 25,
            "humidity": 30,
            "wind_speed": 2,
            "weather_main": "Clear",
        }
        self.assertEqual(calculate_weather_score(row), 100)

    def test_uncomfortable_conditions_receive_low_score(self):
        row = {
            "temperature": 40,
            "humidity": 90,
            "wind_speed": 10,
            "weather_main": "Rain",
        }
        self.assertEqual(calculate_weather_score(row), 5)

    def test_score_and_recommendation_are_added_without_mutating_input(self):
        original = pd.DataFrame([{
            "temperature": 25,
            "humidity": 30,
            "wind_speed": 2,
            "weather_main": "Clear",
        }])
        result = add_weather_scores(original)
        self.assertEqual(result.loc[0, "weather_score"], 100)
        self.assertEqual(result.loc[0, "recommendation"], "Excellent")
        self.assertNotIn("weather_score", original.columns)


if __name__ == "__main__":
    unittest.main()
