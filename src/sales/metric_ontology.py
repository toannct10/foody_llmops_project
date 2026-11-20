"""Stable Sales metric meanings and result units shared by both execution paths."""

import re

UNITS = {
    "delivered_sales": "VND",
    "order_count": "orders",
    "cancelled_order_count": "orders",
    "cancelled_order_value": "VND",
    "cancellation_rate": "%",
    "refunded_order_count": "orders",
    "refunded_order_value": "VND",
    "refund_rate": "%",
    "average_order_value": "VND/order",
    "aov": "VND/order",  # Existing response contract.
}
STATUS_METRICS = {"cancelled_order_count", "cancelled_order_value",
                  "refunded_order_count", "refunded_order_value"}
MONETARY_WORDS = ("so tien", "tong tien", "gia tri", "doanh thu", "amount", "value")


def detect_metrics(value):
    """Classify status, unit, and quantity before generic order words."""
    cancelled = bool(re.search(r"\bhuy\b|cancel", value))
    refunded = bool(re.search(r"\bhoan\b|refund", value))
    rate = bool(re.search(r"ty le|ti le|\brate\b|phan tram|%|cancellation", value))
    money = any(word in value for word in MONETARY_WORDS)
    average = bool(re.search(r"\baov\b|gia tri (?:trung binh )?don(?: hang)?|"
                             r"gia tri don(?: hang)? trung binh", value))
    if cancelled:
        status = ("cancellation_rate" if rate else
                  "cancelled_order_value" if money else "cancelled_order_count")
    elif refunded:
        status = ("refund_rate" if rate else
                  "refunded_order_value" if money else "refunded_order_count")
    else:
        status = None
    if status and " va " not in value:
        return (status,)
    metrics = []
    if any(word in value for word in ("doanh thu", "revenue", "sales")) and \
            (not status or " va " in value):
        metrics.append("delivered_sales")
    if any(word in value for word in ("so don", "don hang", "orders")) and \
            (not status or re.search(r"so don\s+va\b", value)) and \
            (not average or re.search(r"so don\s+va\b", value)):
        metrics.append("order_count")
    if average:
        metrics.append("average_order_value")
    if status:
        metrics.append(status)
    return tuple(metrics or ("delivered_sales",))
