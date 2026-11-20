"""One final Sales view-model, continuous progress, and sourced sidebar status."""

from streamlit.testing.v1 import AppTest

from src.ui.progress import progress_markup
from src.ui.sales_view import normalize_sales_result


def test_progress_is_continuous_accessible_and_hides_internal_stage():
    markup = progress_markup("Sales", "Execute <query>", 0.61, 1.8)
    assert 'aria-valuenow="61"' in markup
    assert 'class="foody-progress-track"' in markup
    assert 'class="foody-progress-fill" style="width:61%"' in markup
    assert "foody-progress-block" not in markup
    assert "Execute" not in markup
    assert "1.8 s elapsed" in markup
    assert "tokens" not in markup
    complete = progress_markup("Sales", "Completed", 1, 2, state="complete")
    assert 'aria-valuenow="100"' in complete
    assert "Analysis complete" in complete
    assert "foody-progress complete" in complete


def test_progress_palette_motion_and_reduced_motion():
    from src.ui.styles import CSS

    assert "#7C3AED" in CSS and "#6366F1" in CSS and "#3B82F6" in CSS
    assert "foody-shimmer" in CSS and "foody-pulse" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert ".foody-progress.complete .foody-progress-fill" in CSS
    assert ".foody-progress.complete .foody-progress-block" not in CSS


def test_enterprise_kpi_scale_and_three_workspace_contract():
    from app.app import WORKSPACES
    from src.ui.styles import CSS

    assert WORKSPACES == ("Sales Intelligence", "Review Intelligence", "System Monitor")
    assert "font-variant-numeric:tabular-nums" in CSS
    assert ".foody-kpi-primary .foody-kpi-value" in CSS
    assert ".foody-kpi-healthy .foody-kpi-value" in CSS


def test_verified_sales_numbers_precede_sql_and_keep_exact_values():
    result = {"answer": "Verified yearly revenue", "status": "ok",
              "execution_mode": "QWEN_TEXT_TO_SQL",
              "query_plan": {"intent": "compare_periods", "metric": "delivered_sales",
                             "periods": ["2025", "2026"]},
              "display_rows": [{"year": 2025, "delivered_sales": 10540272},
                               {"year": 2026, "delivered_sales": 7654352}],
              "sql_details": {"sql": "SELECT year, delivered_sales FROM verified_mart"}}
    app = AppTest.from_string("from src.ui.sales_view import show_sales_result\n"
                              f"show_sales_result({result!r})\n").run()
    assert not app.exception
    markup = [item.value for item in app.markdown]
    assert any("foody-kpi-primary" in item and "10.540.272" in item for item in markup)
    assert any("foody-kpi-primary" in item and "7.654.352" in item for item in markup)
    assert next(i for i, item in enumerate(markup) if "foody-kpi-primary" in item) < next(
        i for i, item in enumerate(markup) if "Generated SQL" in item)
    assert len(app.code) == 1


def test_sales_chart_cards_render_with_observed_values():
    snapshot = {"monthly": [{"period_start": "2025-05-01", "delivered_sales": 100,
                             "mom_growth": .1},
                            {"period_start": "2025-06-01", "delivered_sales": 80,
                             "mom_growth": -.2}],
                "weekly": [{"period_start": "2025-05-05", "delivered_sales": 40}],
                "statuses": [{"order_status": "Delivered", "order_count": 2}]}
    app = AppTest.from_string("from src.ui.sales_view import _charts\n"
                              f"_charts({snapshot!r})\n").run()
    assert not app.exception
    titles = " ".join(item.value for item in app.subheader)
    for title in ("Monthly Revenue", "Weekly Revenue", "Month-over-Month Growth",
                  "Order Status"):
        assert title in titles


def test_year_aggregate_previews_aggregate_not_unlabeled_months():
    result = {
        "answer": "Tổng doanh thu năm 2025 là 300 ₫.", "status": "ok",
        "execution_mode": "DETERMINISTIC_FALLBACK",
        "analysis": {"intent": "YEAR_AGGREGATE", "metric": "delivered_sales",
                     "periods": ["2025-01", "2025-02"], "aggregation": "total",
                     "details": {"aggregate_value": 300}},
        "sql_facts": {"2025-01": {"delivered_sales": 100},
                      "2025-02": {"delivered_sales": 200}},
        "display_rows": [{"period": "2025-01", "value": 100},
                         {"period": "2025-02", "value": 200}],
        "sql_details": {"sql": None, "fallback_reason": "local_mode"},
    }
    view = normalize_sales_result(result)
    assert view.preview_title == "Aggregate Result"
    assert view.preview_rows == ({"Aggregate": "Total revenue", "Period": "2025-01 – 2025-02",
                                  "Value": "300 ₫"},)
    assert view.technical["displayed_rows"] == len(view.preview_rows) == 1
    assert view.technical["source_fact_rows"] == 2
    assert view.sql is None
    assert view.mode == "DETERMINISTIC_FALLBACK"
    app = AppTest.from_string("from src.ui.sales_view import show_sales_result\n"
                              f"show_sales_result({result!r})\n").run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert len(app.code) == 0
    assert any("Aggregate Result" in item.value for item in app.markdown)


def test_month_set_render_cannot_inherit_prior_year_result():
    yearly = {"answer": "2025 total", "status": "ok",
              "execution_mode": "QWEN_TEXT_TO_SQL",
              "query_plan": {"intent": "YEAR_AGGREGATE", "metric": "delivered_sales",
                             "periods": [f"2025-{month:02d}" for month in range(1, 13)],
                             "aggregation": "sum"},
              "display_rows": [{"delivered_sales": 1000}]}
    monthly = {"answer": "May + June total", "status": "ok",
               "execution_mode": "QWEN_TEXT_TO_SQL",
               "query_plan": {"intent": "RANGE_AGGREGATE", "metric": "delivered_sales",
                              "periods": ["2025-05", "2025-06"],
                              "aggregation": "sum"},
               "display_rows": [{"delivered_sales": 100}]}
    assert ("Period", "2025-01 – 2025-12") in normalize_sales_result(yearly).kpis
    view = normalize_sales_result(monthly)
    assert view.preview_rows == ({"Aggregate": "Total revenue",
                                  "Period": "2025-05 – 2025-06", "Value": "100 ₫"},)
    assert ("Period", "2025-05 – 2025-06") in view.kpis
    assert ("Value", "100 ₫") in view.kpis
    assert "2025-01" not in str(view)


def test_fallback_drops_superseded_qwen_sql_and_timing():
    result = {"answer": "Fallback answer", "status": "ok",
              "execution_mode": "DETERMINISTIC_FALLBACK",
              "sql_details": {"sql": "SELECT stale_qwen_result", "tables_used": ["stale_table"],
                              "generation_latency_ms": 999, "input_tokens": 25,
                              "validation_status": "SQL validated before execution",
                              "fallback_reason": "result_mismatch"},
              "display_rows": [{"period": "2026-05", "value": 100}],
              "analysis": {"metric": "delivered_sales", "response_mode": "FACTUAL"}}
    view = normalize_sales_result(result)
    assert view.sql is None
    assert view.technical["tables"] == []
    assert view.technical["generation_ms"] is None
    assert view.technical["input_tokens"] is None
    assert view.technical["fallback_reason"] == "result_mismatch"
    assert view.technical["validation"] == "Qwen SQL not executed"
    assert view.preview_rows[0]["Revenue"] == "100 ₫"


def test_blocked_result_has_no_stale_preview_or_verified_badge():
    result = {"answer": "Blocked", "status": "refused_unsafe_request",
              "execution_mode": "DETERMINISTIC_FALLBACK",
              "sql_details": {"sql": "SELECT stale"},
              "display_rows": [{"period": "2026-05", "value": 100}]}
    view = normalize_sales_result(result)
    assert view.preview_rows == ()
    assert view.sql is None
    assert view.answer_badge == "Blocked"
    assert view.technical["displayed_rows"] == 0


def test_sidebar_renders_pipeline_status_and_stack():
    app = AppTest.from_string(
        "from src.ui import sidebar\n"
        "sidebar._pipeline_status = lambda: {'status':'SUCCESS', "
        "'last_success_utc':'2026-11-08T12:00:00+00:00'}\n"
        "sidebar.render_sidebar_details()\n"
    ).run()
    assert not app.exception
    sidebar = " ".join(item.value for item in app.sidebar.markdown)
    assert "Runtime" in sidebar
    assert "SUCCESS" in sidebar
    assert "PostgreSQL" in sidebar
    assert "RAG V3" in sidebar
    assert "Text-to-SQL + fallback" in sidebar
    assert "Airflow" in sidebar
