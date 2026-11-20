{{ config(materialized='view') }}

with totals as (
    select restaurant_id,
           sum(order_count) as order_count, sum(gross_sales) as gross_sales,
           sum(delivered_sales) as delivered_sales,
           sum(delivered_count) as delivered_count,
           sum(cancelled_count) as cancelled_count,
           sum(refunded_count) as refunded_count
    from {{ ref('restaurant_daily_sales') }}
    group by restaurant_id
)
select *,
       {{ sales_aov('delivered_sales', 'delivered_count') }} as aov,
       {{ cancellation_rate('cancelled_count', 'order_count') }} as cancellation_rate,
       {{ refund_rate('refunded_count', 'order_count') }} as refund_rate
from totals
