# Text-to-SQL implementation audit

Audited at commit `65eadd4` before implementation. Existing Sales routing is in
`src/sales/router.py`; the deterministic plan, predefined SQL, calculation and
answer paths are `src/sales/{planner,queries,analysis,comparisons,response,service}.py`.
The UI is `src/ui/sales_view.py`, including Sales and Cross Analysis. PostgreSQL
connections come from `src/warehouse/loader.py`. The local Qwen2.5-3B llama.cpp
server is configured in `qwen_v3_3b.yaml`; `src/llm/gateway.py` already provides
JSON-schema chat completions and `src/rag_v3/cli.py` selects its frozen artifact.
SQLite LLMOps logging and Prometheus metrics are in `src/rag/monitoring.py` and
`src/monitoring/metrics.py`.

Migration `sql/postgres/migrations/003_sales.sql` defines `dim_sales_restaurant`,
`fact_order`, `dim_date` (in `001_init.sql`), and the `restaurant_daily_sales`,
`restaurant_weekly_sales`, `restaurant_monthly_sales`,
`restaurant_sales_summary`, and `restaurant_order_status_summary` views.
`004_review_ids.sql` adds the current Review ID relationship. The Text-to-SQL
allowlist will expose only the Sales dimension and aggregate views needed for a
question, using their migration-defined columns. It will not expose raw orders,
Review tables, state tables, or the whole database. Revenue means Delivered
revenue; AOV is Delivered revenue divided by Delivered count; cancellation and
refund rates divide by all observed orders.

The running PostgreSQL instance was checked read-only on 2026-11-06: `fact_order`
has 400,000 rows, `dim_sales_restaurant` 3,647,
`restaurant_monthly_sales` 76,402, `restaurant_weekly_sales` 223,679, and
`restaurant_sales_summary` 3,647. These are the actual marts used by the
allowlist; only `restaurant_monthly_sales`, `restaurant_weekly_sales`,
`restaurant_sales_summary`, and `dim_sales_restaurant` are exposed to Qwen.

Changes: add a Sales schema selector, versioned prompt, structured-output parser,
AST policy validator, read-only PostgreSQL executor, Qwen orchestration, bounded
telemetry, Sales UI details, tests, and documentation. Keep the existing planner as
fallback/reference, the three workspaces, Review RAG V3, its embedding and
grounding path, and the current Cross restaurant/date evidence gates.

Risks: Qwen can be unavailable or emit invalid SQL; validation must prevent any
execution and fall back. The selected restaurant must be scoped in non-ranking
questions. Large query results and slow plans need row and time limits. Qwen has
a 2048-token context in Compose, so schema selection must stay small. Local
Review2 uses PostgreSQL, although the original proposal mentioned Snowflake.
