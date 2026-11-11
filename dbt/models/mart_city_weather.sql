with latest_daily_observations as (
    select
        * exclude (observation_rank),
        cast(event_timestamp as date) as observation_date
    from (
        select
            *,
            row_number() over (
                partition by city, cast(event_timestamp as date)
                order by event_timestamp desc
            ) as observation_rank
        from {{ ref('stg_weather') }}
    )
    where observation_rank = 1
),
scored as (
    select
        *,
        case
            when temperature between 20 and 28 then 40
            when (temperature >= 15 and temperature < 20)
              or (temperature > 28 and temperature <= 32) then 20
            else 5
        end
        + case
            when humidity < 40 then 30
            when humidity < 60 then 20
            when humidity < 80 then 10
            else 0
        end
        + case
            when wind_speed < 3 then 20
            when wind_speed < 5 then 15
            when wind_speed < 8 then 10
            else 0
        end
        + case
            when weather_main in ('Clear', 'Sunny') then 10
            when weather_main = 'Clouds' then 5
            else 0
        end as weather_score
    from latest_daily_observations
),
ranked as (
    select
        *,
        row_number() over (
            partition by observation_date
            order by weather_score desc, city
        ) as daily_rank
    from scored
)

select
    *,
    case
        when weather_score >= 80 then 'Excellent'
        when weather_score >= 60 then 'Bien'
        when weather_score >= 40 then 'Moyen'
        else 'Déconseillé'
    end as recommendation
from ranked
