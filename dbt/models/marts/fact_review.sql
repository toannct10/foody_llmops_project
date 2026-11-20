{{ config(materialized='incremental', unique_key='review_id', incremental_strategy='merge', on_schema_change='fail') }}

select review_id, restaurant_id, review_date,
       to_number(to_char(review_date, 'YYYYMMDD')) as date_key,
       rating, review_text,
       source_file, source_hash, batch_id, source_loaded_at
from {{ ref('stg_reviews') }}
{% if is_incremental() %}
where source_loaded_at >= (
    select coalesce(max(source_loaded_at), '1900-01-01'::timestamp_tz) from {{ this }}
)
{% endif %}
