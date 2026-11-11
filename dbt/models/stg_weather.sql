with source as (
    select *
    from read_csv_auto(
        '{{ env_var("WEATHER_SILVER_PATH", "weather_silver.csv") }}',
        header = true,
        null_padding = true
    )
)

select
    city,
    country,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(temperature as double) as temperature,
    cast(humidity as integer) as humidity,
    cast(wind_speed as double) as wind_speed,
    weather_main,
    cast(event_timestamp as timestamp) as event_timestamp,
    cast(ingestion_timestamp as timestamp) as ingestion_timestamp
from source
where city is not null
  and event_timestamp is not null
