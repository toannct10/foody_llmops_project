{{ config(materialized='incremental', unique_key='order_id', incremental_strategy='merge', on_schema_change='fail') }}

with typed as (
    select
        trim(order_id) as order_id,
        trim(restaurant_id) as restaurant_id,
        nullif(trim(restaurant_name), '') as restaurant_name,
        try_to_date(order_date, 'YYYY-MM-DD') as order_date,
        try_to_decimal(sales_amount, 14, 2) as sales_amount,
        case lower(trim(order_status))
            when 'delivered' then 'Delivered'
            when 'cancelled' then 'Cancelled'
            when 'refunded' then 'Refunded'
            else null
        end as order_status,
        source_file,
        source_hash,
        batch_id,
        loaded_at as source_loaded_at
    from {{ source('foody_raw', 'SALES_SOURCE') }}
    {% if is_incremental() %}
    where loaded_at >= (
        select coalesce(max(source_loaded_at), '1900-01-01'::timestamp_tz) from {{ this }}
    )
    {% endif %}
), ranked as (
    select *, row_number() over (
        partition by order_id
        order by source_loaded_at desc, batch_id desc, source_hash desc, source_file desc
    ) as source_rank
    from typed
)
select order_id, restaurant_id, restaurant_name, order_date, sales_amount,
       order_status, source_file, source_hash, batch_id, source_loaded_at
from ranked where source_rank = 1
