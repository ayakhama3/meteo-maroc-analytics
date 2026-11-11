select city, event_timestamp
from {{ ref('stg_weather') }}
group by city, event_timestamp
having count(*) > 1
