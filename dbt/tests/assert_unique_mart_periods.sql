with periods as (
    select 'daily' as mart_name, restaurant_id, period_start
    from {{ ref('restaurant_daily_sales') }}
    union all
    select 'weekly', restaurant_id, period_start
    from {{ ref('restaurant_weekly_sales') }}
    union all
    select 'monthly', restaurant_id, period_start
    from {{ ref('restaurant_monthly_sales') }}
    union all
    select 'reviews', restaurant_id, period_start
    from {{ ref('restaurant_monthly_reviews') }}
)
select mart_name, restaurant_id, period_start, count(*) as duplicate_count
from periods
group by mart_name, restaurant_id, period_start
having count(*) > 1
