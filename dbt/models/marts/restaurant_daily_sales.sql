{{ config(materialized='view') }}

with counts as (
    select restaurant_id, order_date as period_start,
           count(*) as order_count,
           sum(sales_amount) as gross_sales,
           {{ delivered_revenue('sales_amount', 'order_status') }} as delivered_sales,
           {{ delivered_orders('order_status') }} as delivered_count,
           sum(case when order_status = 'Cancelled' then 1 else 0 end) as cancelled_count,
           sum(case when order_status = 'Refunded' then 1 else 0 end) as refunded_count
    from {{ ref('fact_order') }}
    where order_date <= to_date(convert_timezone('Asia/Ho_Chi_Minh', current_timestamp()))
    group by restaurant_id, order_date
)
select *,
       {{ sales_aov('delivered_sales', 'delivered_count') }} as aov,
       {{ cancellation_rate('cancelled_count', 'order_count') }} as cancellation_rate,
       {{ refund_rate('refunded_count', 'order_count') }} as refund_rate
from counts
