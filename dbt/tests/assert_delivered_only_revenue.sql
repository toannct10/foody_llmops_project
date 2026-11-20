with expected as (
    select restaurant_id, order_date as period_start,
           sum(case when order_status = 'Delivered' then sales_amount else 0 end)
               as delivered_sales,
           sum(case when order_status = 'Delivered' then 1 else 0 end)
               as delivered_count,
           sum(case when order_status = 'Cancelled' then 1 else 0 end)
               as cancelled_count,
           count(*) as order_count
    from {{ ref('fact_order') }}
    where order_date <= to_date(convert_timezone('Asia/Ho_Chi_Minh', current_timestamp()))
    group by restaurant_id, order_date
)
select e.restaurant_id, e.period_start
from expected e left join {{ ref('restaurant_daily_sales') }} d
  on d.restaurant_id = e.restaurant_id and d.period_start = e.period_start
where d.restaurant_id is null
   or d.delivered_sales <> e.delivered_sales
   or d.delivered_count <> e.delivered_count
   or d.cancellation_rate <> round(e.cancelled_count / nullif(e.order_count, 0), 4)
