# Foody enterprise analytics UI architecture

The Streamlit app retains three workspaces: Sales Intelligence, Review Intelligence, and System Monitor. Shared colors, card borders, spacing, badges, and KPI styles live in `src/ui/styles.py` and `src/ui/components.py`.

## Design system

The dark palette uses `#0B0F17` for the page, `#131A24` and `#17202D` for surfaces, and soft slate borders. Violet `#7C3AED`, indigo `#6366F1`, and blue `#3B82F6` identify primary activity; cyan `#22D3EE` is a highlight. Muted green `#6BCB9A` is reserved for confirmed success, amber `#F5B85A` for warnings, and rose `#FF6B7A` for failures. Text uses `#F8FAFC` and `#94A3B8`. Cards share radius, padding, border, and a restrained one-pixel hover lift. Navigation remains the sidebar's most prominent element, followed by compact system status and stack summaries.

The typography stack is Inter where installed, followed by system UI fonts. Page titles are 28–32 px, section titles about 22 px, card labels about 12 px, primary KPI values 30–36 px, secondary values about 22–25 px, and body copy 14–16 px. KPI digits are tabular. Labels use moderate weight and letter spacing; technical code alone uses a monospace stack. The sidebar keeps navigation stronger than its small, muted runtime and stack summaries. Active navigation has an indigo left accent.

`kpi_card` defines primary, secondary, status, and health variants. A primary figure gets the largest type and a restrained indigo top accent. Health colors are reserved for success, warning, and failure states. Cards use 18–20 px inner padding, soft borders and shadows, and at most a one-pixel hover lift. Narrow screens stack Streamlit columns and wrap values without clipping.

Review Intelligence has two tabs. **Analyze a Review** performs ad-hoc, in-memory inference with the same `normalize()` and `review_migration.enrich()` path as production Review enrichment, using the pinned TF-IDF sentiment and aspect artifacts. The models are cached per Streamlit process. The tab stores only its current result in session state; it does not write the text to Foody data, PostgreSQL, SQLite, Chroma, or BM25 and makes no Qwen call. **Ask Review AI** retains the existing restaurant, review explorer, and RAG interface.

The saved aspect artifact predicts `ambiance`, `amenities`, `cleanliness`, `food`, `location`, `overall`, `price`, `room`, and `service`. It has no separate Staff, Menu, or Parking outputs. The UI displays actual labels and uncalibrated model scores without translating them into unsupported categories or measured Foody accuracy.

## Loading

`src/ui/progress.py` supplies one `AIProgress` component for Sales, Review RAG, and ad-hoc classification. The continuous violet-to-blue track shows a numeric percentage, short business-facing status message, and elapsed time. The shimmer and cyan leading-edge pulse run only while active; completion stays indigo/blue. CSS disables motion under `prefers-reduced-motion`. Stages advance only at observable UI/backend boundaries: request checking, connection or filter setup, the combined backend call, and result preparation. Percentage is an estimate, not token or SQL substage telemetry. The active elapsed label updates at those boundaries; the measured final duration appears below the answer.

## Sales answer and SQL

The final backend response is normalized once into `SalesRenderModel` and saved with the restaurant/question scope. Verified Analysis, primary verified figures, supporting KPI cards, Result Preview, SQL, and Technical Details render in that order from one object. Year/range totals preview the aggregate itself; the number of displayed rows in Technical Details equals the rendered table row count. Source fact rows are reported separately. For `QWEN_TEXT_TO_SQL`, service-returned SQL is displayed with `st.code(..., language="sql")` and completed validation/execution badges. For `DETERMINISTIC_FALLBACK`, superseded Qwen SQL, tables, and timing are hidden; the UI names the predefined parameterized route and explains that its SQL text is not exposed. Blocked requests show no SQL or stale preview. The collapsed Technical Details panel groups execution, database, performance, and verification metadata without credentials or bound parameter values.

The Sales dashboard puts delivered revenue first, orders and AOV next, and cancellation/refund rates in a secondary row. Monthly Revenue spans the full width; Weekly Revenue and Month-over-Month Growth share the next row; Order Status follows. Revenue charts use thicker indigo/cyan lines, compact axis numbers, subtle grid lines, and exact currency tooltips. Growth bars use cyan for positive and rose for negative, without changing source values. Empty states replace charts when no observations exist. The final result uses a muted indigo-accent answer card, hierarchy-aware KPIs, distinct SQL badge tones, and a preview matched to the result type. Aggregates show the one verified total, trends show a chart and table, and comparisons show paired period cards. Bound parameter values and credentials remain hidden.

## Review cards and session state

`review_text` renders one version of each comment: full short text, a truncated preview, or full expanded text. Its More/Less button uses a stable review ID and a hash of the restaurant/question context. Expanding replaces the preview in the same card. Sales, Review, and Cross answers are stored in Streamlit session state with restaurant/question scopes, so widget reruns render saved results and do not repeat SQL, RAG, or Qwen calls. Changing the scope hides the previous answer. Technical details remain collapsed by default.

## System Monitor

Monitoring status badges use live Prometheus target values. The top row prioritizes System Health, Pipeline Status, RAG Requests, and API Error Rate. Sales Queries, Average AI Latency, and Token Usage appear in the supporting row. KPI, operations, cost, alert, and model evaluation content continues to use the existing read-only data sources. The sidebar names integrations without implying that they are healthy until checked.

Status text distinguishes `HEALTHY`, `DEGRADED`, `DOWN`, and `NOT CONFIGURED`; color is supplementary. The monitor keeps its AI Operations, Data Platform, System Health, DevOps + LLMOps, Cost & Alerts, and Model Evaluation sections. Native Streamlit charts and tables use consistent dark containers without new front-end dependencies.

Keyboard controls retain visible focus rings. The process bar includes an ARIA progress value, all status chips include text, and narrow layouts retain wrapped card text and horizontally scrollable SQL. Motion is subtle and disabled for reduced-motion users.

The compact sidebar Runtime card reads the existing Airflow pipeline ledger for the latest status and successful update timestamp. Current stack names describe the configured components; they are not health checks.
