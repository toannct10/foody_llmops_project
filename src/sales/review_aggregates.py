"""Exact-ID, bounded monthly Review aggregates for Cross Intelligence."""

from datetime import date

from src.sales.semantic_plan import next_month


def monthly_review_aggregate(conn, restaurant_id, period):
    """Count model predictions, not manually annotated sentiment labels."""
    start = date.fromisoformat(period + "-01")
    end = date.fromisoformat(next_month(period) + "-01")
    parameters = (str(restaurant_id), start, end)
    cursor = conn.execute("""SELECT COUNT(*) AS review_count,
        COUNT(*) FILTER (WHERE r.predicted_sentiment='positive') AS positive_count,
        COUNT(*) FILTER (WHERE r.predicted_sentiment='neutral') AS neutral_count,
        COUNT(*) FILTER (WHERE r.predicted_sentiment='negative') AS negative_count
        FROM fact_review_v2 r JOIN dim_date d ON d.date_key=r.date_key
        WHERE r.restaurant_id=%s AND d.calendar_date >= %s
        AND d.calendar_date < %s""", parameters)
    row = dict(zip((item.name for item in cursor.description), cursor.fetchone(), strict=True))
    cursor = conn.execute("""SELECT a.aspect, COUNT(*) AS review_count
        FROM fact_review_v2 r JOIN dim_date d ON d.date_key=r.date_key
        CROSS JOIN LATERAL jsonb_array_elements_text(r.predicted_aspects) AS a(aspect)
        WHERE r.restaurant_id=%s AND d.calendar_date >= %s
        AND d.calendar_date < %s
        GROUP BY a.aspect ORDER BY review_count DESC, a.aspect""", parameters)
    aspects = {str(aspect): int(count) for aspect, count in cursor.fetchall()}
    count = int(row["review_count"])
    counts = {key: int(row[key]) for key in
              ("positive_count", "neutral_count", "negative_count")}
    return {"period": period, "review_count": count, **counts,
            "sentiment_rate": {label: counts[label + "_count"] / count if count else None
                               for label in ("positive", "neutral", "negative")},
            "aspect_frequencies": aspects,
            "label_source": "production_sentiment_and_aspect_predictions"}
