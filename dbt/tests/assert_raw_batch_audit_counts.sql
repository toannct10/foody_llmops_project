with observed as (
    select 'sales' as source_name, batch_id, count(*) as row_count
    from {{ source('foody_raw', 'SALES_SOURCE') }}
    group by batch_id
    union all
    select 'reviews' as source_name, batch_id, count(*) as row_count
    from {{ source('foody_raw', 'REVIEWS_SOURCE') }}
    group by batch_id
), audited as (
    select source_name, batch_id, max(row_count) as row_count, count(*) as audit_records
    from {{ source('foody_raw', 'LOAD_AUDIT') }}
    group by source_name, batch_id
)
select o.source_name, o.batch_id, o.row_count, a.row_count as audited_count
from observed o left join audited a
    on a.source_name = o.source_name and a.batch_id = o.batch_id
where a.row_count is null or a.audit_records <> 1 or o.row_count <> a.row_count
