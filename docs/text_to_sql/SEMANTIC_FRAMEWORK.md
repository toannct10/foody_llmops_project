# Sales semantic planning and verification

The Sales path builds one immutable `CanonicalPlan` before SQL generation. Its
fields are `operation`, `metrics`, `time_scope`, `group_by`, `filters`,
`sort`, `limit`, `output_shape`, and `include_breakdown`. The independent
temporal parser expands every requested month, including continuous ranges,
and records inclusive start and exclusive end bounds for each comparison side.
It recognizes month lists, numeric month notation, quarters, half-years,
full years, multiple years, and relative YoY/MoM periods. The operation is
selected separately from the time scope.

Plan validation rejects unsupported metrics/operations, invalid or overlapping
months, missing ranking limits, trends without monthly grouping, comparisons
without two sides, and scalar plans with contradictory grouping. Qwen receives
the validated plan along with the relevant schema and business definitions.
The existing SQL AST/security and read-only execution checks remain in force.
The SQL verifier additionally checks bounds, metrics, grouping, ordering,
limits, output shape, and ratio numerator/denominator aggregation. After SQL
execution, the result verifier checks comparison sides, trend chronology,
ranking order/count, period scope, and breakdown reconciliation.

The deterministic fallback consumes that same canonical plan. It reads the
predefined, parameterized monthly mart query and applies operation-specific
Python calculations. Rates are recomputed from summed numerators and
denominators. Only observed rows contribute; absent months are listed in
`observed_periods` and `missing_periods`, never inserted as zero rows.
The established simple-month wording and limited historical multi-step plans
retain their existing presentation. The UI selects KPI, comparison, time
series, ranking, or multi-metric presentation using `output_shape`.

## Operation contracts

| Operation | Required result |
| --- | --- |
| aggregate, range_aggregate | One total; optional reconciling breakdown |
| comparison | Every requested side as a separate row |
| trend | Observed time rows in chronological order |
| ranking | Sorted rows, no more than the requested limit |
| growth | Baseline, comparison, absolute and percentage change |
| rate | Ratio from summed numerator and denominator |
| multi_metric | Every named metric in each relevant row |

## Measured acceptance

The 66-question matrix covers all eight operations. Its operation classification
and the ten read-only PostgreSQL checks are recorded by
`python -m scripts.evaluate_sales_semantics` in
`reports/sales/SEMANTIC_FRAMEWORK_EVALUATION.json`. The live checks compare
the returned values against an independent fixed SQL read of the monthly mart.
The one live Qwen range trial in this refactor was rejected as `plan_periods`
after two attempts; the operation-based fallback returned the checked total.
That single trial does not establish a general Qwen SQL accuracy rate.

Unsupported or intentionally bounded classes include unrestricted SQL,
forecasting, causal claims, arbitrary joins, and analytical scopes beyond 100
months. Global restaurant ranking and weekly requests retain their established
specialized paths; the canonical monthly fallback is scoped to one restaurant.
