{{ config(materialized='view') }}

with weekly as (
    select restaurant_id,
           dateadd(day, 1 - dayofweekiso(period_start), period_start)::date as period_start,
           sum(order_count) as order_count, sum(gross_sales) as gross_sales,
           sum(delivered_sales) as delivered_sales,
           sum(delivered_count) as delivered_count,
           sum(cancelled_count) as cancelled_count,
           sum(refunded_count) as refunded_count
    from {{ ref('restaurant_daily_sales') }}
    group by restaurant_id, dateadd(day, 1 - dayofweekiso(period_start), period_start)::date
)
select cur.*,
       {{ sales_aov('cur.delivered_sales', 'cur.delivered_count') }} as aov,
       {{ cancellation_rate('cur.cancelled_count', 'cur.order_count') }} as cancellation_rate,
       {{ refund_rate('cur.refunded_count', 'cur.order_count') }} as refund_rate,
       prev.delivered_sales as previous_delivered_sales,
       round((cur.delivered_sales - prev.delivered_sales) /
             nullif(prev.delivered_sales, 0), 4) as wow_growth
from weekly cur
left join weekly prev on prev.restaurant_id = cur.restaurant_id
    and prev.period_start = dateadd(week, -1, cur.period_start)
