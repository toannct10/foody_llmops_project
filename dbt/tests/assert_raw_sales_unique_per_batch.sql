-- A new immutable source batch may repeat order IDs from earlier batches.
select batch_id, trim(order_id) as order_id, count(*) as duplicate_count
from {{ source('foody_raw', 'SALES_SOURCE') }}
group by batch_id, trim(order_id)
having count(*) > 1
