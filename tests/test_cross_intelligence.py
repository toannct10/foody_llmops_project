"""Cross Intelligence must never join or explain beyond verified observations."""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.rag.schemas import ReviewHit
from src.sales import cross_intelligence as cross
from src.sales.review_aggregates import monthly_review_aggregate
from src.sales.semantic_plan import parse_time_scope

QUESTION = ("Doanh thu tháng 6/2025 thay đổi thế nào so với tháng 5/2025 "
            "và khách hàng đang phản hồi gì?")


def aggregate(period, count=2, negative=1):
    return {"period": period, "review_count": count,
            "positive_count": count - negative, "neutral_count": 0,
            "negative_count": negative,
            "sentiment_rate": {"positive": (count - negative) / count if count else None,
                               "neutral": 0 if count else None,
                               "negative": negative / count if count else None},
            "aspect_frequencies": {"service": negative},
            "label_source": "production_sentiment_and_aspect_predictions"}


def evidence(period="2025-06", restaurant_id="1062", text="Phục vụ hơi chậm trong bữa tối"):
    return {"ref": "E1", "review_id": "review-1", "restaurant_id": restaurant_id,
            "period": period, "date": period + "-15", "text": text,
            "sentiment": "negative", "aspects": '["service"]', "source": "foody"}


def test_cross_plan_preserves_explicit_periods_and_exact_id():
    plan = cross.build_cross_plan(QUESTION, "1062")
    assert plan.mode == "cross_analysis"
    assert plan.restaurant_id == "1062"
    assert plan.periods == ("2025-06", "2025-05")
    assert set(plan.review_metrics) >= {"review_count", "negative_count",
                                        "sentiment_rate", "aspect_frequencies"}
    assert plan.need_review_evidence


def test_shared_year_period_comes_from_existing_sales_parser():
    question = "Doanh thu tháng 6/2025 giảm so với tháng 5 và review ra sao?"
    assert parse_time_scope(question).periods == ("2025-06", "2025-05")
    assert cross.build_cross_plan(question, "1062").periods == ("2025-06", "2025-05")


@pytest.mark.parametrize(("question", "mode"), [
    ("doanh thu tháng 6/2025 giảm", "sales_only"),
    ("doanh thu tháng 6/2025 tăng", "sales_only"),
    ("tháng 6/2025 doanh thu giảm", "sales_only"),
    ("review tiêu cực tháng 6/2025 tăng không?", "review_only"),
    ("Doanh thu tháng 6/2025 giảm có đi kèm với review tiêu cực tăng không?",
     "cross_analysis"),
])
def test_one_month_change_infers_previous_month(question, mode):
    plan = cross.build_cross_plan(question, "1062")
    assert plan.mode == mode
    assert plan.operation == "comparison"
    assert plan.periods == ("2025-05", "2025-06")
    assert plan.baseline_period == "2025-05"
    assert plan.current_period == "2025-06"
    assert plan.period_source == "inferred_previous_month"
    assert {"negative_review_count", "negative_review_rate"} <= set(plan.review_metrics)


def test_plain_month_aggregate_has_no_inferred_baseline():
    plan = cross.build_cross_plan("doanh thu tháng 6/2025 là bao nhiêu?", "1062")
    assert plan.periods == ("2025-06",)
    assert plan.operation != "comparison"
    assert plan.baseline_period is None


def test_january_change_rolls_back_to_december():
    plan = cross.build_cross_plan("doanh thu tháng 1/2026 giảm", "1062")
    assert plan.periods == ("2025-12", "2026-01")


def test_month_without_year_requires_context_or_clarification():
    question = "Doanh thu tháng 6 giảm có đi kèm review tiêu cực tăng không?"
    with pytest.raises(ValueError, match="Please specify the year for month 6"):
        cross.build_cross_plan(question, "1062")
    plan = cross.build_cross_plan(question, "1062", analysis_year=2025)
    assert plan.periods == ("2025-05", "2025-06")


@pytest.mark.parametrize(("question", "baseline", "current", "size"), [
    ("doanh thu năm 2025 giảm có đi kèm review tiêu cực tăng không?",
     "2024", "2025", 24),
    ("doanh thu quý 1 năm 2026 giảm có đi kèm review tiêu cực tăng không?",
     "2025-Q4", "2026-Q1", 6),
])
def test_year_and_quarter_use_previous_comparable_period(question, baseline,
                                                          current, size):
    plan = cross.build_cross_plan(question, "1062")
    assert (plan.baseline_period, plan.current_period) == (baseline, current)
    assert len(plan.periods) == size
    assert plan.operation == "comparison"


def test_cross_default_periods_are_marked_as_inferred():
    plan = cross.build_cross_plan("Doanh thu giảm có đi kèm review tiêu cực tăng không?",
                                 "1062", default_periods=("2025-05", "2025-06"))
    assert plan.periods == ("2025-05", "2025-06")
    assert plan.period_source == "latest_common_observed_periods"


def test_unspecified_period_uses_latest_exact_id_common_months():
    class Connection:
        def execute(self, sql, params):
            assert "r.restaurant_id=s.restaurant_id" in sql
            assert params == ("1062", date(2026, 11, 1))
            return SimpleNamespace(fetchall=lambda: [(date(2026, 6, 1),),
                                                      (date(2026, 5, 1),)])

    assert cross._default_periods(Connection(), "1062", date(2026, 11, 13)) == (
        "2026-05", "2026-06")


def test_review_aggregate_matches_exact_id_and_half_open_month():
    calls = []

    class Cursor:
        description = [SimpleNamespace(name=name) for name in
                       ("review_count", "positive_count", "neutral_count", "negative_count")]

        def fetchone(self):
            return (4, 1, 1, 2)

        def fetchall(self):
            return [("service", 2), ("food", 1)]

    class Connection:
        def execute(self, sql, params):
            calls.append((sql, params))
            return Cursor()

    result = monthly_review_aggregate(Connection(), "1062", "2025-06")
    assert result["review_count"] == 4
    assert result["sentiment_rate"]["negative"] == 0.5
    assert result["aspect_frequencies"]["service"] == 2
    assert len(calls) == 2
    assert all(params == ("1062", date(2025, 6, 1), date(2025, 7, 1))
               for _, params in calls)
    assert all("r.restaurant_id=%s" in sql for sql, _ in calls)


def test_sales_qwen_facts_must_equal_postgres_rows(monkeypatch):
    rows = [{"period_start": date(2025, 5, 1), "delivered_sales": Decimal("100"),
             "order_count": 2, "aov": Decimal("50"), "cancellation_rate": Decimal("0"),
             "refund_rate": Decimal("0")},
            {"period_start": date(2025, 6, 1), "delivered_sales": Decimal("80"),
             "order_count": 2, "aov": Decimal("40"), "cancellation_rate": Decimal("0"),
             "refund_rate": Decimal("0")}]
    monkeypatch.setattr(cross.queries, "monthly_sales_range", lambda *args: rows)
    from src.sales import service

    generated = {"execution_mode": "QWEN_TEXT_TO_SQL",
                 "sql_details": {"semantic_verification": "PASS", "sql": "SELECT ..."},
                 "sql_facts": [{"period_start": "2025-05-01", "delivered_sales": 100},
                               {"period_start": "2025-06-01", "delivered_sales": 80}]}
    monkeypatch.setattr(service, "sales_answer", lambda *args, **kwargs: generated)
    facts, details = cross._sales_facts(None, "1062", ("2025-05", "2025-06"),
                                       QUESTION, date(2026, 1, 1))
    assert [row["delivered_sales"] for row in facts] == [100, 80]
    assert details["mode"] == "QWEN_TEXT_TO_SQL"
    generated["sql_facts"][1]["delivered_sales"] = 81
    _, details = cross._sales_facts(None, "1062", ("2025-05", "2025-06"),
                                   QUESTION, date(2026, 1, 1))
    assert details["mode"] == "PREDEFINED_PARAMETERIZED_SQL"


def test_retrieval_rejects_other_restaurant_and_period():
    def hit(review_id, restaurant_id, stamp):
        return ReviewHit(review_id=review_id, restaurant_name="A", text="Phục vụ chậm",
                         score=0.5, metadata={"restaurant_id": restaurant_id,
                                              "review_timestamp": stamp,
                                              "predicted_sentiment": "negative"})

    class Retriever:
        def search_debug(self, request):
            assert request.restaurant_id == "1062"
            assert request.date_from.date() == date(2025, 6, 1)
            return [hit("right", "1062", "2025-06-15"),
                    hit("wrong-id", "999", "2025-06-15"),
                    hit("wrong-month", "1062", "2025-07-02")], 1.0, {}

    items, details = cross._review_evidence(Retriever(), "1062",
                                            [aggregate("2025-06")], QUESTION)
    assert [item["review_id"] for item in items] == ["right"]
    assert details["searched_periods"] == ["2025-06"]


@pytest.mark.parametrize("raw", [
    {"review_quote": "Phục vụ hơi chậm trong bữa tối", "evidence_ref": "E2"},
    {"review_quote": "Dịch vụ gây ra doanh thu giảm", "evidence_ref": "E1"},
    {"review_quote": "Quán hoàn toàn không tồn tại", "evidence_ref": "E1"},
])
def test_causation_and_grounding_guard_rejects_unsupported_output(raw):
    with pytest.raises(ValueError):
        cross.validate_cross_quote(raw, [evidence()])


@pytest.mark.parametrize("answer", [
    "Service gây ra doanh thu giảm [E1].",
    "Review cùng kỳ ghi [E2].",
])
def test_final_answer_guard_rejects_causation_or_unknown_citation(answer):
    with pytest.raises(ValueError):
        cross.validate_cross_answer(answer, [evidence()])


def _stub_cross(monkeypatch, *, sales=True, reviews=True, evidence_items=None):
    monkeypatch.setattr(cross, "new_corpus_active", lambda: True)
    monkeypatch.setattr(cross.queries, "restaurant", lambda *args: {
        "restaurant_id": "1062", "restaurant_name": "A",
        "review_restaurant_id": "1062"})
    monkeypatch.setattr(cross, "_default_periods", lambda *args: ("2025-05", "2025-06"))
    facts = ([{"period": "2025-05", "delivered_sales": 100,
               "order_count": 2, "aov": 50, "cancellation_rate": 0, "refund_rate": 0},
              {"period": "2025-06", "delivered_sales": 80,
               "order_count": 2, "aov": 40, "cancellation_rate": 0, "refund_rate": 0}]
             if sales else [])
    monkeypatch.setattr(cross, "_sales_facts", lambda *args: (
        facts, {"mode": "PREDEFINED_PARAMETERIZED_SQL", "sql": "SELECT ...",
                "semantic_verification": "PASS" if facts else "NO_DATA",
                "missing_periods": [] if facts else ["2025-05", "2025-06"]}))
    monkeypatch.setattr(cross, "monthly_review_aggregate", lambda _c, _id, period:
                        aggregate(period, count=2, negative=1) if reviews else
                        aggregate(period, count=0, negative=0))
    monkeypatch.setattr(cross, "_review_evidence", lambda *args: (
        evidence_items if evidence_items is not None else [evidence()],
        {"method": "RAG_V2_RRF", "searched_periods": ["2025-06"],
         "filters": {"restaurant_id": "1062", "periods": ["2025-06"]}}))
    from src.sales import service

    monkeypatch.setattr(service, "_record", lambda *args, **kwargs: None)


def test_synthesis_input_contains_only_verified_structured_data(monkeypatch):
    _stub_cross(monkeypatch)
    captured = {}

    class Gateway:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def generate(self, **kwargs):
            captured.update(kwargs)
            return {"review_quote": "Phục vụ hơi chậm trong bữa tối",
                    "evidence_ref": "E1"}, {}

    result = cross.analyze_cross(None, "1062", QUESTION, today=date(2026, 1, 1),
                                 retriever_factory=lambda: object(),
                                 gateway_factory=Gateway)
    payload = json.loads(captured["user"])
    assert set(payload) == {"sales_facts", "sales_drivers", "review_signals",
                            "review_evidence", "missing_data"}
    assert payload["sales_facts"][1]["delivered_sales"] == 80
    assert payload["review_evidence"][0]["period"] == "2025-06"
    assert "[E1]" in result["answer"]
    assert "không chứng minh nhân quả" in result["answer"]
    assert "REVIEW EVIDENCE:" in result["answer"]
    assert "POSSIBLE EXPLANATION: Chưa xác lập được mối liên hệ" in result["answer"]
    assert result["technical"]["causation_guard_status"] == "PASS"


def test_rejected_qwen_quote_does_not_become_arbitrary_explanation(monkeypatch):
    _stub_cross(monkeypatch)

    class Gateway:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def generate(self, **kwargs):
            return {"review_quote": "Review gây ra doanh thu giảm",
                    "evidence_ref": "E1"}, {}

    result = cross.analyze_cross(None, "1062", QUESTION, today=date(2026, 1, 1),
                                 retriever_factory=lambda: object(),
                                 gateway_factory=Gateway)
    assert result["status"] == "grounded"
    assert "Phục vụ hơi chậm trong bữa tối" in result["answer"]
    assert "[E1]" in result["answer"]
    assert "REVIEW EVIDENCE:" in result["answer"]
    assert "POSSIBLE EXPLANATION: Review cùng kỳ ghi" not in result["answer"]
    assert result["technical"]["causation_guard_status"] == "REJECTED_QWEN_FALLBACK"
    assert result["technical"]["generation_mode"] == "deterministic_verified_quote"


def test_missing_review_data_is_explicit_and_skips_qwen(monkeypatch):
    _stub_cross(monkeypatch, reviews=False)
    result = cross.analyze_cross(None, "1062", QUESTION, today=date(2026, 1, 1),
                                 gateway_factory=lambda: pytest.fail("Qwen must not run"))
    assert result["status"] == "no_review_data"
    assert "Không có review cùng kỳ" in result["answer"]
    assert "Thiếu Review: 2025-05, 2025-06" in result["missing_data"]


def test_missing_sales_data_is_explicit(monkeypatch):
    _stub_cross(monkeypatch, sales=False)
    result = cross.analyze_cross(None, "1062", QUESTION, today=date(2026, 1, 1),
                                 retriever_factory=lambda: object(),
                                 gateway_factory=lambda: pytest.fail("Qwen must not run"))
    assert result["status"] == "no_sales_data"
    assert "Không có dữ liệu Sales" in result["answer"]
    assert "Thiếu Sales: 2025-05, 2025-06" in result["missing_data"]


def test_inferred_comparison_uses_observed_direction_and_both_review_rates(
        monkeypatch):
    _stub_cross(monkeypatch, evidence_items=[])
    result = cross.analyze_cross(
        None, "1062",
        "Doanh thu tháng 6/2025 tăng có đi kèm review tiêu cực tăng không?",
        today=date(2026, 1, 1), retriever_factory=lambda: object(),
        gateway_factory=lambda: pytest.fail("Qwen is not needed for numeric facts"))
    assert result["plan"]["baseline_period"] == "2025-05"
    assert result["plan"]["current_period"] == "2025-06"
    assert "Chênh lệch Delivered -20 VND (-20.00%)" in result["answer"]
    assert "Doanh thu giảm" in result["answer"]
    assert "số review tiêu cực không đổi" in result["answer"]
    assert "tỷ lệ review tiêu cực không đổi" in result["answer"]
    assert "không chứng minh nhân quả" in result["answer"]


def test_missing_baseline_sales_does_not_claim_comparison(monkeypatch):
    _stub_cross(monkeypatch, reviews=False)
    monkeypatch.setattr(cross, "_sales_facts", lambda *_: (
        [{"period": "2025-06", "delivered_sales": 80}],
        {"mode": "PREDEFINED_PARAMETERIZED_SQL", "sql": "SELECT ...",
         "semantic_verification": "NO_DATA", "missing_periods": ["2025-05"]}))
    result = cross.analyze_cross(
        None, "1062",
        "Doanh thu tháng 6/2025 giảm có đi kèm review tiêu cực tăng không?",
        today=date(2026, 1, 1))
    assert result["status"] == "insufficient_sales_comparison"
    assert "Thiếu Sales: 2025-05" in result["missing_data"]
    assert "Chưa đủ hai kỳ Sales" in result["answer"]


def test_missing_one_review_month_preserves_sales_comparison(monkeypatch):
    _stub_cross(monkeypatch, reviews=False, evidence_items=[])
    monkeypatch.setattr(cross, "monthly_review_aggregate", lambda _c, _id, period:
                        aggregate(period, count=2, negative=1) if period == "2025-06"
                        else aggregate(period, count=0, negative=0))
    result = cross.analyze_cross(
        None, "1062",
        "Doanh thu tháng 6/2025 giảm có đi kèm review tiêu cực tăng không?",
        today=date(2026, 1, 1), retriever_factory=lambda: object(),
        gateway_factory=lambda: pytest.fail("Qwen is not needed for numeric facts"))
    assert result["status"] == "insufficient_review_comparison"
    assert "Chênh lệch Delivered -20 VND" in result["answer"]
    assert "Không đủ Review ở cả hai kỳ" in result["answer"]
    assert "Thiếu Review: 2025-05" in result["missing_data"]


def test_exact_id_join_refuses_unmatched_restaurant(monkeypatch):
    monkeypatch.setattr(cross, "new_corpus_active", lambda: True)
    monkeypatch.setattr(cross.queries, "restaurant", lambda *args: {
        "restaurant_id": "1062", "restaurant_name": "A",
        "review_restaurant_id": "999"})
    result = cross.analyze_cross(None, "1062", QUESTION)
    assert result["status"] == "unmatched_restaurant"
    assert "trùng chính xác" in result["answer"]
