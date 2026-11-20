-- AI-facing monthly status measures; no order-level identifiers or raw fact access.
CREATE OR REPLACE VIEW restaurant_monthly_order_status_values AS
SELECT o.restaurant_id,
       DATE_TRUNC('month', d.calendar_date)::DATE AS period_start,
       COUNT(*)::INTEGER AS order_count,
       COUNT(*) FILTER (WHERE o.order_status = 'Cancelled')::INTEGER
           AS cancelled_order_count,
       COALESCE(SUM(o.sales_amount) FILTER (WHERE o.order_status = 'Cancelled'), 0)
           AS cancelled_order_value,
       COUNT(*) FILTER (WHERE o.order_status = 'Refunded')::INTEGER
           AS refunded_order_count,
       COALESCE(SUM(o.sales_amount) FILTER (WHERE o.order_status = 'Refunded'), 0)
           AS refunded_order_value,
       ROUND(COUNT(*) FILTER (WHERE o.order_status = 'Cancelled')::NUMERIC /
             NULLIF(COUNT(*), 0), 4) AS cancellation_rate,
       ROUND(COUNT(*) FILTER (WHERE o.order_status = 'Refunded')::NUMERIC /
             NULLIF(COUNT(*), 0), 4) AS refund_rate
FROM fact_order o JOIN dim_date d ON d.date_key = o.date_key
WHERE d.calendar_date <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE
GROUP BY o.restaurant_id, DATE_TRUNC('month', d.calendar_date)::DATE;
