with expected as (
    select count(*) as order_count from {{ ref('fact_order') }}
    where order_date <= to_date(convert_timezone('Asia/Ho_Chi_Minh', current_timestamp()))
), observed as (
    select 'daily' as mart_name, sum(order_count) as order_count
    from {{ ref('restaurant_daily_sales') }}
    union all
    select 'weekly', sum(order_count) from {{ ref('restaurant_weekly_sales') }}
    union all
    select 'monthly', sum(order_count) from {{ ref('restaurant_monthly_sales') }}
    union all
    select 'summary', sum(order_count) from {{ ref('restaurant_sales_summary') }}
), review_observed as (
    select coalesce(sum(review_count), 0) as row_count
    from {{ ref('restaurant_monthly_reviews') }}
), review_expected as (
    select count(*) as row_count from {{ ref('fact_review') }}
)
select o.mart_name, o.order_count, e.order_count as expected_order_count
from observed o cross join expected e
where coalesce(o.order_count, 0) <> e.order_count
union all
select 'reviews', o.row_count, e.row_count
from review_observed o cross join review_expected e
where o.row_count <> e.row_count
