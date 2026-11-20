"""Shared Prometheus metrics for API and Streamlit RAG V3 requests."""

from threading import Lock

from prometheus_client import Counter, Gauge, Histogram, start_http_server

API_REQUESTS = Counter("foody_api_requests_total", "HTTP requests", ["route", "status"])
API_DURATION = Histogram("foody_api_request_duration_seconds", "HTTP latency", ["route"])
RAG_REQUESTS = Counter("foody_rag_requests_total", "RAG V3 requests", ["status"])
GENERATION = Counter("foody_rag_generation_mode_total", "RAG generation modes",
                     ["generation_mode"])
RETRIEVAL = Counter("foody_rag_retrieval_route_total", "RAG retrieval routes", ["route"])
EVIDENCE = Histogram("foody_rag_evidence_count", "Cited review count")
LLM_LATENCY = Histogram(
    "foody_llm_latency_seconds", "LLM generation latency",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, float("inf")),
)
INPUT_TOKENS = Counter("foody_llm_input_tokens_total", "LLM input tokens")
OUTPUT_TOKENS = Counter("foody_llm_output_tokens_total", "LLM output tokens")
SALES_QUERIES = Counter("foody_sales_queries_total", "SQL sales questions", ["status"])
CROSS_REQUESTS = Counter("foody_cross_analysis_requests_total", "Cross-analysis questions", ["status"])
SALES_DURATION = Histogram("foody_sales_sql_duration_seconds", "SQL sales question latency")
TEXT_SQL_REQUESTS = Counter("text_to_sql_requests_total", "Qwen Sales SQL attempts")
TEXT_SQL_SUCCESS = Counter("text_to_sql_success_total", "Validated Sales SQL executions")
TEXT_SQL_VALIDATION_FAILURES = Counter(
    "text_to_sql_validation_failures_total", "Rejected Sales SQL", ["reason"])
TEXT_SQL_EXECUTION_FAILURES = Counter(
    "text_to_sql_execution_failures_total", "Sales SQL execution failures")
TEXT_SQL_FALLBACK = Counter("text_to_sql_fallback_total", "Deterministic Sales fallbacks")
TEXT_SQL_GENERATION_LATENCY = Histogram(
    "text_to_sql_generation_latency_seconds", "Sales SQL generation latency")
TEXT_SQL_EXECUTION_LATENCY = Histogram(
    "text_to_sql_execution_latency_seconds", "Sales SQL execution latency")
TEXT_SQL_TOTAL_LATENCY = Histogram(
    "text_to_sql_total_latency_seconds", "Sales Text-to-SQL total latency")
TEXT_SQL_INPUT_TOKENS = Counter("text_to_sql_input_tokens_total", "Sales SQL input tokens")
TEXT_SQL_OUTPUT_TOKENS = Counter("text_to_sql_output_tokens_total", "Sales SQL output tokens")
TEXT_SQL_TABLES = Counter("text_to_sql_selected_tables_total", "Approved Sales marts selected",
                          ["table"])
TEXT_SQL_MODES = Counter("text_to_sql_execution_mode_total", "Sales execution modes", ["mode"])
MODEL_GATEWAY_REQUESTS = Counter(
    "foody_model_gateway_requests_total", "Model gateway generation calls",
    ["model", "task", "status"])
MODEL_GATEWAY_LATENCY = Histogram(
    "foody_model_gateway_latency_seconds", "Model gateway generation latency",
    ["model", "task"])
MODEL_GATEWAY_INPUT_TOKENS = Counter(
    "foody_model_gateway_input_tokens_total", "Model gateway input tokens",
    ["model", "task"])
MODEL_GATEWAY_OUTPUT_TOKENS = Counter(
    "foody_model_gateway_output_tokens_total", "Model gateway output tokens",
    ["model", "task"])
MODEL_STRUCTURED_FAILURES = Counter(
    "foody_llm_structured_output_failures_total", "Invalid LLM structured output",
    ["model", "task"])
RAG_INSUFFICIENT = Counter("foody_rag_insufficient_evidence_total",
                           "RAG requests with insufficient evidence")
RAG_FALLBACK = Counter("foody_rag_fallback_total", "RAG extractive fallbacks")
RAG_GROUNDING = Counter("foody_rag_grounding_total", "RAG grounding outcomes", ["status"])
RAG_RETRIEVAL_LATENCY = Histogram("foody_rag_retrieval_latency_seconds",
                                  "RAG retrieval duration")
PIPELINE_LAST_FAILURE = Gauge("foody_pipeline_last_run_failed",
                              "Last non-fixture local Airflow run failed", ["source"])
PIPELINE_QUALITY_FAILED = Gauge("foody_pipeline_quality_gate_failed",
                                "Last non-fixture data quality gate failed", ["source"])
PIPELINE_LAST_SUCCESS = Gauge("foody_pipeline_last_success_timestamp_seconds",
                              "Last accepted local Airflow publication time", ["source"])
PIPELINE_DURATION = Gauge("foody_pipeline_last_duration_seconds",
                          "Last non-fixture local Airflow run duration", ["source"])
PIPELINE_ROWS = Gauge("foody_pipeline_last_rows", "Last local Airflow row counts",
                      ["kind"])
HOST_MEMORY_RATIO = Gauge("foody_host_memory_usage_ratio",
                          "Host memory fraction visible to the application container")
VISIBLE_CPU_PERCENT = Gauge("foody_visible_cpu_percent", "CPU use visible to backend")
VISIBLE_GPU_PERCENT = Gauge("foody_visible_gpu_percent", "GPU use when nvidia-smi is available",
                            ["device"])
VISIBLE_VRAM_BYTES = Gauge("foody_visible_vram_used_bytes",
                           "GPU memory used when nvidia-smi is available", ["device"])
PROCESS_RSS = Gauge("foody_process_resident_memory_bytes", "Backend resident memory")
LOCAL_ESTIMATED_COST = Gauge("foody_local_estimated_cost",
                             "Opt-in estimated local generation cost in configured currency",
                             ["device"])
SERVICE_HEALTH = Gauge("foody_service_health", "Bounded service health: 1 up, 0 down",
                       ["service"])

_SERVER_LOCK = Lock()
_SERVER_STARTED = False
_STATUSES = {"grounded", "supported_extractive_fallback", "correct_insufficient",
             "insufficient_evidence", "error"}
_MODES = {"qwen", "extractive_fallback", "none"}
_ROUTES = {"TREND_CAUSATION", "SERVICE_COMPLAINT", "FOOD_COMPLAINT",
           "PRICE_COMPLAINT", "GENERAL_ASPECT", "GENERAL_SUMMARY"}


def observe_model_gateway(model, task, status, duration_seconds,
                          input_tokens=None, output_tokens=None,
                          structured_failure=False):
    """Record bounded model/task/status labels without prompt or SQL content."""
    model = model if model in {"qwen", "llama", "deepseek"} else "other"
    task = task if task in {"text_to_sql", "review", "cross"} else "other"
    status = "success" if status == "valid_json" else "failure"
    MODEL_GATEWAY_REQUESTS.labels(model=model, task=task, status=status).inc()
    MODEL_GATEWAY_LATENCY.labels(model=model, task=task).observe(duration_seconds)
    MODEL_GATEWAY_INPUT_TOKENS.labels(model=model, task=task).inc(input_tokens or 0)
    MODEL_GATEWAY_OUTPUT_TOKENS.labels(model=model, task=task).inc(output_tokens or 0)
    if structured_failure:
        MODEL_STRUCTURED_FAILURES.labels(model=model, task=task).inc()


def start_streamlit_metrics(port):
    """Expose Streamlit's own process metrics once across script reruns/sessions."""
    global _SERVER_STARTED
    with _SERVER_LOCK:
        if not _SERVER_STARTED:
            start_http_server(int(port), addr="0.0.0.0")
            _SERVER_STARTED = True


def observe_rag_error():
    RAG_REQUESTS.labels(status="error").inc()


def observe_rag(telemetry):
    # These labels are internally generated bounded enums, never raw query/user IDs.
    status = telemetry.get("status")
    mode = telemetry.get("generation_mode")
    route = telemetry.get("query_route")
    status = status if status in _STATUSES else "other"
    mode = mode if mode in _MODES else "other"
    route = route if route in _ROUTES else "other"
    RAG_REQUESTS.labels(status=status).inc()
    GENERATION.labels(generation_mode=mode).inc()
    RETRIEVAL.labels(route=route).inc()
    EVIDENCE.observe(telemetry.get("evidence_count") or 0)
    if status in {"insufficient_evidence", "correct_insufficient"}:
        RAG_INSUFFICIENT.inc()
    if mode == "extractive_fallback":
        RAG_FALLBACK.inc()
    RAG_GROUNDING.labels(status=status).inc()
    if telemetry.get("retrieval_latency_ms") is not None:
        RAG_RETRIEVAL_LATENCY.observe(telemetry["retrieval_latency_ms"] / 1000)
    if telemetry.get("llm_latency_ms") is not None:
        LLM_LATENCY.observe(telemetry["llm_latency_ms"] / 1000)
    INPUT_TOKENS.inc(telemetry.get("input_tokens") or 0)
    OUTPUT_TOKENS.inc(telemetry.get("output_tokens") or 0)


def observe_sales_sql(duration_seconds, status):
    """Record one SQL answer with bounded status labels."""
    SALES_QUERIES.labels(status=status if status in {"ok", "no_data", "error"} else "other").inc()
    SALES_DURATION.observe(duration_seconds)


def observe_cross_analysis(status):
    CROSS_REQUESTS.labels(status=status if status in {
        "grounded", "no_aligned_reviews", "unmatched_restaurant", "no_sales_data",
        "insufficient_review_evidence", "error",
    } else "other").inc()


def observe_text_to_sql(status, generation_ms, execution_ms, total_ms, *, reason=None,
                        input_tokens=0, output_tokens=0, tables=()):
    """Content-free counters; rejection labels come from fixed policy categories."""
    if status == "success":
        TEXT_SQL_REQUESTS.inc()
        TEXT_SQL_SUCCESS.inc()
        TEXT_SQL_MODES.labels(mode="QWEN_TEXT_TO_SQL").inc()
        for table in tables:
            if table in {"restaurant_monthly_sales", "restaurant_weekly_sales",
                         "restaurant_sales_summary", "dim_sales_restaurant"}:
                TEXT_SQL_TABLES.labels(table=table).inc()
    elif status == "validation_failure":
        TEXT_SQL_VALIDATION_FAILURES.labels(reason=reason if reason in {
            "structured_output", "answer_type", "sql_comments", "multiple_statements",
            "sql_syntax", "non_select", "unsafe_operation", "unsupported_subquery",
            "table_allowlist", "cross_schema", "column_allowlist", "function_allowlist",
            "row_limit", "parameters", "restaurant_scope", "result_limit",
            "unsafe_expression", "unsafe_join", "wildcard_select",
            "business_definition", "period_scope", "result_scope", "result_mismatch",
        } else "other").inc()
    elif status == "execution_failure":
        TEXT_SQL_EXECUTION_FAILURES.inc()
    elif status == "fallback":
        TEXT_SQL_REQUESTS.inc()
        TEXT_SQL_FALLBACK.inc()
        TEXT_SQL_MODES.labels(mode="DETERMINISTIC_FALLBACK").inc()
    if status in {"success", "fallback"}:
        TEXT_SQL_GENERATION_LATENCY.observe(generation_ms / 1000)
        TEXT_SQL_EXECUTION_LATENCY.observe(execution_ms / 1000)
        TEXT_SQL_TOTAL_LATENCY.observe(total_ms / 1000)
    TEXT_SQL_INPUT_TOKENS.inc(input_tokens or 0)
    TEXT_SQL_OUTPUT_TOKENS.inc(output_tokens or 0)
