# Sales Text-to-SQL architecture

The original proposal mentioned Snowflake. The current Review2 local warehouse is
PostgreSQL. This implementation addresses the proposal's natural-language-to-SQL,
validation and read-only execution requirement on the actual local warehouse.

```text
Sales question → deterministic Sales router → relevant Sales mart selector
→ existing Qwen2.5-3B llama.cpp gateway → JSON SQL draft
→ PostgreSQL AST/policy validator → read-only, timed PostgreSQL execution
→ verified rows (single-month scalars cross-checked against the predefined mart)
→ deterministic Vietnamese result renderer
            ↘ on failure: existing deterministic Sales planner/queries/renderer

Review question → unchanged Review RAG V3: metadata filters → BM25/MiniLM/RRF
→ evidence packet → Qwen2.5-3B → grounding/citation gate

Cross question → existing verified restaurant_id/date alignment
→ deterministic SQL facts and optional independently checked Text-to-SQL facts
+ same-period Review RAG evidence → guarded synthesis
```

The Text-to-SQL path is enabled in the Review2 Streamlit Compose service. In
source-only/CI runs it is opt-in with `TEXT_TO_SQL_ENABLED=true`. The deterministic
path remains the reference and fallback. `src/sales/text_to_sql.py` owns schema
selection, structured output, policy, executor and result rendering. `src/sales/service.py`
chooses the path, and `src/ui/sales_view.py` shows SQL/validation/mode in an
expander. `src/monitoring/metrics.py` exposes bounded counters and latency.

Qwen generates SQL and grounded Review/Cross wording. It does not execute SQL,
create embeddings, replace sentiment/aspect classifiers, or bypass validation.
MiniLM remains the dense embedding model. Only the approved Sales marts and
`dim_sales_restaurant` are shared with the SQL prompt; raw order and Review tables
are absent. See `TEXT_TO_SQL_SECURITY.md` for exact gates.
