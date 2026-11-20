{{ config(materialized='view') }}

select restaurant_id, date_trunc('month', review_date)::date as period_start,
       count(*) as review_count, count(rating) as rating_count,
       round(avg(rating), 2) as average_rating
from {{ ref('fact_review') }}
group by restaurant_id, date_trunc('month', review_date)::date
