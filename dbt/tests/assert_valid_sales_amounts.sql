select order_id, sales_amount
from {{ ref('stg_sales') }}
where sales_amount is null or sales_amount < 0
