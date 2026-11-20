# UI/UX acceptance

Date: 2026-11-08. Local Compose stack and live Streamlit browser at `http://127.0.0.1:8501`.

| Check | Result | Evidence |
| --- | --- | --- |
| Three workspaces | PASS | Sales Intelligence, Review Intelligence, System Monitor visible in sidebar. |
| Sales question | PASS | Restaurant 2751, “Doanh thu tháng 5/2026 của nhà hàng 2751 là bao nhiêu?” returned verified delivered revenue **3,184,032 ₫**; PostgreSQL `restaurant_monthly_sales` row matched. |
| Sales loading | PASS | Stage label “Generating, validating and executing SQL” observed during request. No token-level progress claimed. |
| SQL visibility | PASS | Generated SQL appeared immediately below Verified Analysis, with `QWEN_TEXT_TO_SQL` and Generated/Validated/Read-only/Executed/Verified badges. |
| Technical Details | PASS | Collapsed panel opened with Execution, Database, Performance, and Verification sections. |
| Review question | PASS | Valid current restaurant Đen Đá Cafe; question about drinks and service returned an evidence fallback answer citing E1, with 1 evidence card and metadata. |
| Review loading | PASS | “Retrieving evidence and generating a grounded answer” observed during request. |
| Evidence More/Less | PASS | Long E1 review preview ended in `...`; More replaced it with the full review in the same card; Less restored the preview. No duplicate card text. |
| No AI rerun on More/Less | PASS | SQLite `rag_v3_request` count was 167 before the question, 168 after the question, and 168 after More and Less. |
| System Monitor | PASS | Page rendered without exception; Prometheus targets showed 3/3 healthy. |
| Analyze a Review tab | PASS | Live multi-aspect Vietnamese input returned Positive with a 99.4% uncalibrated model score; Ambiance, Food, Price, and Service badges displayed. |
| Classifier Technical Details | PASS | Expanded panel showed both saved model files, preprocessing, threshold, raw aspect scores, and 142.4 ms measured inference latency. |
| Ask Review AI tab | PASS | Existing restaurant selector, recent reviews, and RAG question form remained visible in the second tab. |
| Classifier container runtime | PASS | Base and overlay images rebuilt with pinned `joblib==1.6.0` and `scikit-learn==1.7.2`, matching the local model runtime. |

The browser capture workflow displayed Sales and Monitor screenshots during inspection. They were not written to the repository. The Review request used `extractive_fallback`; this is reported as the actual generation mode, and the UI did not alter the RAG answer.

Validation: focused UI tests **13 passed**; full suite **504 passed** (one upstream Starlette deprecation warning); Ruff, compileall, demo-preflight, and Compose configuration all passed.

The classifier tab is a later addition. Its focused validation passed **16 tests**, and the full suite passed **512 tests** with one upstream Starlette deprecation warning. Ruff, compileall, and demo-preflight passed. SQLite `rag_v3_request` remained at **168** after the live ad-hoc classification; Chroma and BM25 counts remained **15,454** each in preflight. The model's trained aspect taxonomy differs from a requested display list: it has no separate Staff, Menu, or Parking labels, so those scores are not shown or inferred.

## Segmented progress and Sales consistency update

The live sidebar showed pipeline **SUCCESS** with last successful update at **2026-11-08 07:03 UTC**, plus compact current-stack rows. A live restaurant 2751 full-year 2025 Sales question displayed segmented loading at **61%** during the combined SQL call and **100%** on completion. Its final answer and KPI both showed **10,540,272 ₫**. Qwen SQL failed execution, so the final response used `DETERMINISTIC_FALLBACK`: the SQL section showed the predefined-query note and no stale SQL text. The aggregate preview showed one row with the same **10,540,272 ₫**. Technical Details reported `YEAR_AGGREGATE`, **1 preview row**, **12 source fact rows**, and fallback reason `execution_error`.

The live Review request used the same segmented loading component and completed with one cited E1 evidence card. More replaced the preview with the full comment, Less restored the preview, and SQLite `rag_v3_request` remained **169** after both controls. The existing RAG answer path was unchanged.

Validation for this update: focused UI tests **14 passed**; full suite **517 passed** with one upstream Starlette deprecation warning; Ruff, compileall, and demo-preflight passed.

## Enterprise analytics UI final validation — 2026-11-08

This section supersedes the earlier segmented-progress notes. The three top-level workspaces remain Sales Intelligence, Review Intelligence, and System Monitor. Review Intelligence still has Analyze a Review and Ask Review AI tabs.

The final dark design uses page `#0B0F17`, surfaces `#131A24` / `#17202D`, violet `#7C3AED`, indigo `#6366F1`, blue `#3B82F6`, cyan `#22D3EE`, muted success green `#6BCB9A`, warning amber `#F5B85A`, and error rose `#FF6B7A`. The sidebar places navigation above a compact sourced pipeline status and current stack. KPI cards, chart containers, answer cards, SQL console, badges, and data tables share soft borders and restrained spacing.

At a 1440 × 900 browser viewport, the Sales request for restaurant **2751**, `tổng doanh thu tháng 5 và 6 năm 2025`, showed a continuous violet/indigo/blue process bar at **61%** during the combined backend call and **100%** on completion. The DOM-reported fill used the intended gradient and `foody-shimmer` animation. The final route was `QWEN_TEXT_TO_SQL`; answer, period KPI, and one-row aggregate preview agreed on **2025-05 – 2025-06** and **1,322,736 ₫**. Generated SQL and the multi-tone validation badges were visible, while Technical Details remained collapsed. The year-only question rendered **2025-01 – 2025-12** and **10,540,272 ₫**. PostgreSQL truth was not altered by this UI phase.

The Analyze a Review tab processed `Đồ ăn ngon nhưng phục vụ hơi chậm và giá khá cao.` without exception. It showed **Negative**, an explicitly uncalibrated **80.3% model score**, and Food **69.0%**, Price **60.0%**, and Service **83.3%** detected-label scores. The process bar completed at 100% in indigo/blue. The classifier result remains ad-hoc and does not enter the review corpus.

In Ask Review AI, the existing Đen Đá Cafe selection answered `Khách hàng nhận xét gì về đồ uống và phục vụ?` with **one E1 citation** and `extractive_fallback` generation. Retrieval was `RAG_V2_RRF`, grounding status `ACCEPTED`, and measured end-to-end UI time **74.6 s**. A continuous process bar appeared at 61% and completed at 100%. The evidence card's More button replaced its preview with the complete comment; Less restored the preview. SQLite `rag_v3_request` count stayed **170** before and after both controls, so expansion did not repeat RAG inference.

System Monitor rendered **AI Operations, Data Platform, System Health, DevOps + LLMOps, Cost & Alerts, and Model Evaluation**. A two-series token chart initially exposed a Streamlit color-count exception; the chart now receives separate indigo and cyan colors and the page renders without exception. Immediately after a Streamlit restart, Prometheus status was **DEGRADED, 2/3 targets**; the UI displayed that state accurately. Final browser validation showed **HEALTHY, 3/3 targets**. No fourth workspace was added. The final browser check also measured an indigo selected sidebar radio (`rgb(99, 102, 241)`) and indigo Review tab indicator (`rgb(129, 140, 248)`).

The process component contains one horizontal track, percent, user-facing status sentence, and elapsed label. Internal Parse/Plan/SQL/Execute stage names are not displayed. A subtle shimmer and active-edge pulse stop at completion; the completed bar remains indigo/blue. `prefers-reduced-motion` disables the animation and transitions. Keyboard focus and status text supplement color.

Validation: focused UI suite **29 passed**; full pytest **532 passed**, with one upstream Starlette deprecation warning; Ruff **PASS**; compileall **PASS**; demo-preflight **PASS**; base and Review-2/Airflow Compose config **PASS**. Browser screenshots were inspected during acceptance and were not added to the repository.

Remaining visual limits: the elapsed label inside an active progress bar updates at observable stage boundaries, so it can show `0.0 s` during a long backend call; the measured final duration is shown below the result. Dense Monitor chart categories retain Streamlit's compact native axis labels. The live `DEGRADED` target count is operational telemetry, not an interface rendering error.

## Final information hierarchy and batch-stack acceptance — 2026-11-09

The active architecture is scheduled batch source → validation → local PostgreSQL or S3/Snowflake → dbt → Airflow → AI/LLMOps → Streamlit. Kafka/KRaft and Terraform were retired because streaming and infrastructure-as-code are outside the proposal. PostgreSQL migrations and Snowflake bootstrap/RBAC SQL moved from `warehouse/` to `sql/postgres/` and `sql/snowflake/`; `warehouse/` is gone. Historical DevOps measurements remain labeled as historical.

The final typography uses Inter when installed with system fallbacks: 28–32 px page title, about 22 px section title, 12 px card label, 30–36 px primary KPI, 22–25 px secondary KPI, and 14–16 px body. KPI digits are tabular. Primary values have a subtle indigo accent; health green, warning amber, and failure rose retain their status meanings. Sidebar navigation is stronger than compact runtime details. The continuous process bar retains percentage, elapsed time, status text, reduced-motion support, and violet/indigo/blue fill.

At a 1440 × 900 browser viewport, Sales Intelligence showed a 36 px Delivered Revenue figure, supporting order/AOV values, and rates in a secondary row. Monthly Revenue spans the full content width, Weekly Revenue and Month-over-Month Growth share the next row, and Order Status follows. Revenue charts use indigo/cyan lines, compact axes, subtle grids, and exact-value tooltips; growth bars distinguish positive cyan from negative rose. No chart data or SQL facts were changed.

Live restaurant 2751 question `tổng doanh thu tháng 5 và tháng 6 năm 2025` completed in **82.1 s**. The continuous bar was observed at **61%** and **100%**. Verified Analysis and the primary **1,322,736 ₫** KPI agreed with the one-row aggregate preview; May was **773,840 ₫** and June **548,896 ₫**. The final mode was `DETERMINISTIC_FALLBACK`. The Fallback Query panel remained visible below the business result, with executed/verified badges; its SQL text was unavailable from this route and was not invented for display. Technical Details stayed collapsed. The Sales charts and cards rendered without exception.

Analyze a Review classified `Đồ ăn rất ngon, phục vụ chu đáo, tôi rất hài lòng.` as **Positive**. Its primary sentiment card was larger than the secondary **98.4% uncalibrated model score**. Food **75.5%** and Service **71.0%** used saved aspect scores. The ad-hoc route did not call Qwen or change the review corpus.

Ask Review AI answered `Khách hàng nhận xét gì về đồ uống và phục vụ?` for Đen Đá Cafe in **75.7 s**. The response used one cited E1 evidence card, `RAG_V2_RRF` retrieval, and `ACCEPTED` grounding. The evidence fallback answer and review text rendered without exception. Only presentation changed; RAG generation and retrieval behavior were unchanged.

System Monitor rendered without exception: **HEALTHY**, **2/2** configured monitoring targets reporting, pipeline **SUCCESS**, **240** RAG requests, **82** Sales queries, **12.9 s** average AI latency, and **305,411** tokens. The first row prioritizes health, pipeline, requests, and error rate; supporting numbers follow. Its four top cards were aligned after visual inspection. Exactly three workspaces remain.

Validation after the substantial UI edits: focused UI suite **47 passed**; full pytest **557 passed**, one upstream Starlette deprecation warning; Ruff, compileall, demo-preflight, security scan, Compose configuration, ten Prometheus rules, offline dbt parse, and both Airflow DAG imports passed. PostgreSQL, Qwen, backend, Streamlit, Airflow, Prometheus, and Grafana returned HTTP **200** on their health endpoints. The final card-height-only CSS adjustment is covered by the final focused/static pass.

Limits: deterministic fallback does not expose SQL text through the current response contract. Active progress elapsed text updates at observable stages and may show `0.0 s` during a long backend call; measured final duration appears after completion. Live AWS/Snowflake connectivity was outside this local acceptance.
