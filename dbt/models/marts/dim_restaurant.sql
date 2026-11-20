{{ config(materialized='table') }}

with names as (
    select restaurant_id, restaurant_name, count(*) as name_count
    from {{ ref('stg_sales') }}
    where restaurant_name is not null
    group by restaurant_id, restaurant_name
), ranked as (
    select restaurant_id, restaurant_name,
           row_number() over (
               partition by restaurant_id
               order by name_count desc, restaurant_name asc
           ) as name_rank
    from names
), reviewed as (
    select distinct restaurant_id from {{ ref('stg_reviews') }}
)
select s.restaurant_id,
       n.restaurant_name,
       (r.restaurant_id is not null) as has_reviews
from (select distinct restaurant_id from {{ ref('stg_sales') }}) s
left join ranked n on n.restaurant_id = s.restaurant_id and n.name_rank = 1
left join reviewed r on r.restaurant_id = s.restaurant_id
