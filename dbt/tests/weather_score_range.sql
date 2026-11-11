select city, event_timestamp, weather_score
from {{ ref('mart_city_weather') }}
where weather_score < 0 or weather_score > 100
