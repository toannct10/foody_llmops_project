{% macro delivered_revenue(amount, status) -%}
    sum(case when {{ status }} = 'Delivered' then {{ amount }} else 0 end)
{%- endmacro %}

{% macro delivered_orders(status) -%}
    sum(case when {{ status }} = 'Delivered' then 1 else 0 end)
{%- endmacro %}

{% macro cancellation_rate(cancelled_count, all_count) -%}
    round({{ cancelled_count }} / nullif({{ all_count }}, 0), 4)
{%- endmacro %}

{% macro refund_rate(refunded_count, all_count) -%}
    round({{ refunded_count }} / nullif({{ all_count }}, 0), 4)
{%- endmacro %}

{% macro sales_aov(revenue, delivered_count) -%}
    round({{ revenue }} / nullif({{ delivered_count }}, 0), 2)
{%- endmacro %}
