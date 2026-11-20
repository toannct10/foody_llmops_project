{{ config(materialized='incremental', unique_key='order_id', incremental_strategy='merge', on_schema_change='fail') }}

select order_id, restaurant_id, order_date,
       to_number(to_char(order_date, 'YYYYMMDD')) as date_key,
       sales_amount, order_status,
       source_file, source_hash, batch_id, source_loaded_at
from {{ ref('stg_sales') }}
{% if is_incremental() %}
where source_loaded_at >= (
    select coalesce(max(source_loaded_at), '1900-01-01'::timestamp_tz) from {{ this }}
)
{% endif %}
