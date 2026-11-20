{{ config(materialized='incremental', unique_key='review_id', incremental_strategy='merge', on_schema_change='fail') }}

with typed as (
    select
        trim(restaurant_id) as restaurant_id,
        nullif(trim(restaurant_name), '') as restaurant_name,
        nullif(trim(address), '') as address,
        try_to_date(review_time, 'DD/MM/YYYY') as review_date,
        try_to_decimal(rating, 4, 2) as rating,
        regexp_replace(trim("COMMENT"), '[[:space:]]+', ' ') as review_text,
        source_file,
        source_hash,
        batch_id,
        loaded_at as source_loaded_at
    from {{ source('foody_raw', 'REVIEWS_SOURCE') }}
    {% if is_incremental() %}
    where loaded_at >= (
        select coalesce(max(source_loaded_at), '1900-01-01'::timestamp_tz) from {{ this }}
    )
    {% endif %}
), identified as (
    select
        'r26_' || sha2(to_json(array_construct(
            restaurant_id, to_char(review_date, 'YYYY-MM-DD'),
            to_varchar(rating), review_text
        )), 256) as review_id,
        *
    from typed
), ranked as (
    select *, row_number() over (
        partition by review_id
        order by source_loaded_at desc, batch_id desc, source_hash desc, source_file desc
    ) as source_rank
    from identified
)
select review_id, restaurant_id, restaurant_name, address, review_date,
       rating, review_text, source_file, source_hash, batch_id, source_loaded_at
from ranked where source_rank = 1
