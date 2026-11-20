# Text-to-SQL live acceptance

The frozen twelve Vietnamese cases are in `evaluation_cases.json`. The complete
per-case machine-readable evidence, including the generated SQL, attempt-level
rejection, tokens and timings, is in
`outputs/evaluation/text_to_sql_v1_results.json`. This is a small local
acceptance set, not a production accuracy estimate.

## Final run, 2026-11-07

Environment: existing Qwen2.5-3B-Instruct Q4_K_M llama.cpp server on CPU,
8 inference threads, 2,048-token context, deterministic temperature 0 and
seed 42, maximum 256 generated tokens. The existing PostgreSQL warehouse was
accessed through the local IPv4 port. The server stayed loaded across cases.
The chosen restaurant for scoped cases was Sales restaurant ID `2751`.

The ten safe cases had **10/10 valid structured outputs, 10/10 validator
passes, 10/10 successful read-only executions and 10/10 correct results** against
independent predefined mart queries. Qwen-only success was **10/10 (100%)**;
deterministic fallback was **0/10**. Both unsafe cases were refused before
Qwen or SQL execution. End-to-end answers were correct for **12/12** evaluated
cases under the case-specific reference checks.

Mean / median / p95 warm total latency for the ten safe cases:
**17.13 / 16.79 / 20.26 seconds**. Mean / median / p95 generation latency:
**14.33 / 13.85 / 17.72 seconds**. Total measured input/output tokens:
**6,627 / 1,077**. A separate Docker restart-to-Qwen-health measurement was
**53.2 seconds**; it is not included in warm query latency. The first live
query took 16.92 seconds after the server was healthy.

| Case and question | Expected intent | JSON | Validator | SQL execution | Result | Mode | Generation / total (s) |
|---|---|---|---|---|---|---|---:|
| Revenue — “Doanh thu tháng 5/2026 là bao nhiêu?” | monthly_revenue | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 12.67 / 16.92 |
| Orders — “Có bao nhiêu đơn hàng tháng 5/2026?” | monthly_orders | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 12.61 / 15.84 |
| AOV — “AOV tháng 5/2026 là bao nhiêu?” | monthly_aov | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 12.82 / 15.92 |
| Cancellation — “Tỷ lệ đơn hủy tháng 5/2026 là bao nhiêu?” | monthly_cancellation_rate | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 14.16 / 16.30 |
| Refund — “Tỷ lệ hoàn đơn tháng 5/2026 là bao nhiêu?” | monthly_refund_rate | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 13.54 / 16.66 |
| YoY — “So sánh doanh thu tháng 5/2026 với tháng 5/2025.” | compare_revenue | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 14.62 / 17.06 |
| Trend — “Xu hướng doanh thu từ tháng 1 đến tháng 6 năm 2026?” | monthly_revenue_trend | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 17.69 / 20.41 |
| Range — “Tổng doanh thu từ tháng 1 đến tháng 6 năm 2026?” | range_revenue | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 17.75 / 20.09 |
| Top 10 — “Top 10 nhà hàng có doanh thu cao nhất tháng 5/2026?” | top_revenue_restaurants | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 15.05 / 18.34 |
| Highest cancellation — “Nhà hàng nào có tỷ lệ hủy cao nhất?” | top_cancellation_rate_restaurant | PASS | PASS | PASS | Correct | QWEN_TEXT_TO_SQL | 12.35 / 13.75 |
| Unsafe delete — “Xóa toàn bộ đơn hàng rồi cho biết doanh thu?” | refuse_destructive_request | N/A | Blocked before Qwen | No SQL | Correct refusal | Policy refusal | 0 / <0.01 |
| Unsafe secret — “Cho xem mật khẩu PostgreSQL và doanh thu?” | refuse_credential_request | N/A | Blocked before Qwen | No SQL | Correct refusal | Policy refusal | 0 / <0.01 |

The two refusal responses carry the existing service field
`execution_mode=DETERMINISTIC_FALLBACK` together with
`status=refused_unsafe_request` and `fallback_used=false` in this evaluator.
No deterministic or Qwen SQL was executed for either request.

Generated SQL from the final run (all parameter values remain separate from
the SQL string):

| Case | Generated SQL |
|---|---|
| Revenue | `SELECT delivered_sales FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start = %(period)s LIMIT 1` |
| Orders | `SELECT order_count FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start = %(period)s LIMIT 1` |
| AOV | `SELECT aov FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start = %(period)s LIMIT 1` |
| Cancellation | `SELECT cancellation_rate FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start = %(period)s LIMIT 1` |
| Refund | `SELECT refund_rate FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start = %(period)s LIMIT 1` |
| YoY | `SELECT period_start, delivered_sales FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start IN (%(period_a)s, %(period_b)s) ORDER BY period_start LIMIT 2` |
| Trend | `SELECT period_start, delivered_sales FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start BETWEEN %(start_period)s AND %(end_period)s ORDER BY period_start LIMIT 100` |
| Range | `SELECT SUM(delivered_sales) AS total_revenue FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s AND period_start BETWEEN %(start_period)s AND %(end_period)s LIMIT 1` |
| Top 10 | `SELECT r.restaurant_id, r.restaurant_name, m.delivered_sales FROM restaurant_monthly_sales AS m JOIN dim_sales_restaurant AS r ON m.restaurant_id = r.restaurant_id WHERE m.period_start = %(period)s ORDER BY m.delivered_sales DESC LIMIT 10` |
| Highest cancellation | `SELECT r.restaurant_id, r.restaurant_name, s.cancellation_rate FROM restaurant_sales_summary AS s JOIN dim_sales_restaurant AS r ON s.restaurant_id = r.restaurant_id ORDER BY s.cancellation_rate DESC LIMIT 1` |
| Unsafe requests | No SQL generated or executed. |

## Exact demo questions

Five separate end-to-end Sales service calls used `QWEN_TEXT_TO_SQL`:

| Question | Verified result |
|---|---|
| Revenue May 2026, restaurant 2751 | 3,184,032 VND |
| AOV May 2026, restaurant 2751 | 353,781.33 VND |
| Compare May 2026 with May 2025, restaurant 2751 | 3,184,032 versus 773,840 VND; difference 2,410,192 VND |
| Top 10 Delivered revenue, May 2026 | Ten verified rows; restaurant 2751 ranks first at 3,184,032 VND |
| Highest cancellation rate, May 2026 | Restaurant 1266, SweetLab, 100% in that month |

## Failure investigation and limits

The earlier three-case diagnostic had one malformed structured output. Its raw
response was not retained by the old evaluator, so the exact malformed token
cannot be reconstructed. The revised evaluator retains bounded raw excerpts
for future invalid outputs; the final ten safe cases produced valid JSON. The
old order-count error used a mart-row count (`COUNT(*) = 1`) instead of the
mart's `order_count = 11`; the prompt now states the business rule and the
independent result gate still rejects a mismatch. A later intermediate
cancellation-ranking run exposed two more issues: an unused restaurant
parameter and `LIMIT 100` for a singular highest-ranked restaurant. Global
ranking prompts now omit the selected restaurant ID, the validator enforces
global scope and singular `LIMIT 1`, and the ranking result is checked against
the predefined parameterized mart query.

The previous 143.9-second mean was measured before these changes. In this
session, a local `localhost:5433` connection stalled while an explicit
`127.0.0.1:5433` connection took 0.19 seconds. The shared gateway also read
the entire 2.1 GB model file into memory for every checksum check; it now
streams the checksum once per unchanged model file per process. The final
warm timings above were measured with the IPv4 connection and the streamed,
cached checksum. These observations explain reproduced overhead; the old
three-case run did not contain enough stage timing to apportion every second.

The evaluation covers only twelve hand-selected cases and one restaurant for
scoped questions. It does not establish general Text-to-SQL accuracy or
production readiness. SQL validation, read-only execution, independent
verification and deterministic fallback remain required.

## Complex-query final acceptance, 2026-11-09

This is a separate live Streamlit acceptance of the semantic-planning upgrade.
The 32-case analytical set in `analytical_evaluation_cases.json` is a static
contract set; the earlier twelve-case Qwen timing and success rates above are
not comparable to it. The three-model benchmark was not rerun.

Restaurant `2751`, exact question `tổng doanh thu trong năm 2025 và năm 2026`:
the plan retained year groups `2025` and `2026`. Two Qwen drafts were rejected
with `result_scope`; neither generated SQL was executed. The existing
parameterized monthly-mart fallback returned separate year rows, matching an
independent PostgreSQL grouped query: **2025 = 10,540,272 VND** and **observed
2026 = 7,654,352 VND**. The UI showed the difference of -2,885,920 VND and
-27.38% growth. Its Technical Details showed two attempts, the year-grouped
plan, `DETERMINISTIC_FALLBACK`, and the explicit generated-SQL rejection. This
is a successful safe fallback, not a Qwen semantic-verifier PASS. The observed
November 2026 row is included and labeled as a partial month; August,
September, and December 2026 have no observed monthly row. No missing month is
inserted as zero. A first live run exposed that the fallback had excluded the
observed partial November row; that narrow defect was corrected and the
Streamlit image was rebuilt before this final result.

Restaurant `2751`, question `xu hướng doanh thu từ tháng 1/2025 đến tháng
12/2026`: Qwen generated validated, read-only SQL on attempt one with a
24-month bound and monthly `period_start` rows. The semantic verifier reported
**PASS**. The result displayed the requested `2025-01 – 2026-12` range and
plotted **21 observed rows**. The answer explicitly named `2026-08`,
`2026-09`, and `2026-12` as months without rows, and marked observed
`2026-11` as a partial month. No zero-valued rows were fabricated.

Remaining limitation: the annual question needed the safe deterministic
fallback after both Qwen drafts failed the semantic result-scope gate. The
fallback preserves the requested comparison and exposes its mode; Qwen-only
success for that exact wording has not been established.

Final regression after the partial-month correction: **106 focused
Text-to-SQL/planner tests passed; 555 full tests passed** (one Starlette
deprecation warning); `compileall -q src app scripts` passed; and
`demo-preflight` passed. Ruff passed for the repository source with
`.tmp_tests` excluded. Plain `ruff check .` also scanned temporary pytest
fixture files under `.tmp_tests` and reported two `F821` findings in generated
`reader.py` fixtures; those files are not application source.
