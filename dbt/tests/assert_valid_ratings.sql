select review_id, rating
from {{ ref('stg_reviews') }}
where rating is null or rating < 0 or rating > 10
union all
select review_id, rating
from {{ ref('fact_review') }}
where rating is null or rating < 0 or rating > 10
