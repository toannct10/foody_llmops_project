# Text-to-SQL benchmark failure analysis

This analysis uses the complete live run
`outputs/experiments/llm_benchmark/20261107T022914Z-bccf46ea/`.
All 36 model/question records were produced against the frozen 12-case Sales
mart dataset. The initial comparator did not recognize the nested monthly
facts returned by the deterministic fallback. The corrected scores were
recomputed from the saved live facts without new inference; the original
result files are retained under `initial_scoring/`. The later attempted rerun
stalled on local PostgreSQL and is explicitly marked invalid for comparison.

| Model | Model-result failures on 10 safe cases | End-to-end wrong answers |
|---|---|---|
| Qwen | 0 | 0 |
| Llama | 5 | 1 |
| DeepSeek | 10 | 3 |

## Qwen

All ten safe requests produced structured, validated, executed SQL whose
results matched the frozen reference. There is no observed Qwen failure in
this small set. This does not establish general correctness on unseen SQL
questions.

## Llama

- **YoY comparison:** The generated SQL used `LIMIT 1` for a two-period
  comparison. The query executed, but returned only May 2025 revenue
  (773,840) and omitted May 2026 (3,184,032). The frozen result comparison
  caught the wrong final result. This is a meaningful gap in the existing
  production result gate: that gate did not reject this output. No production
  gate was modified in this benchmark phase.
- **Trend:** The model chose `mom_growth` and a one-month interval for a
  six-month delivered revenue trend. The business-definition gate rejected
  it. The deterministic fallback answered correctly.
- **Range total:** The model covered one month instead of January–June.
  The period gate rejected it; fallback answered correctly.
- **Top revenue and cancellation ranking:** The model gave a wrong period
  parameter for ranking and an incorrectly scoped restaurant filter for
  global cancellation ranking. Both were rejected; fallback answered
  correctly.

Llama's five straightforward single-period questions were correct. The
failures concentrate in comparison, range, and global scope. The visible
failure categories are `wrong_final_result`, `business_rule_misunderstanding`,
`wrong_date_range`, and `wrong_restaurant_scope`.

## DeepSeek

All ten safe requests produced empty structured content in the recorded
gateway attempts (`raw_structured_output` contains empty strings). The JSON
schema gate rejected all ten, so no model SQL reached the validator or
PostgreSQL. The deterministic fallback answered seven correctly. Its AOV,
cancellation-rate, and refund-rate responses used all-time restaurant facts
instead of the requested May 2026 facts, so three final answers were wrong.
The observed category is `invalid_json_or_schema`; the logs alone do not
establish why the model emitted no structured content. The DeepSeek R1
candidate is a 1.5B Qwen-distilled reasoning model with a 256-token output
cap, which is a possible contributing configuration, not a proven cause.
Token counts were unavailable for all ten DeepSeek safe requests and are
reported as unknown rather than zero usage.

## Safety and limits

The two unsafe questions were refused by application policy **before model
invocation** in every run. The 100% unsafe-refusal metric describes the
whole application path, not native model refusal. Prompts, generation settings,
schema, validator, PostgreSQL reference data, and hardware were held constant.
This 12-case set is an acceptance benchmark, not a broad generalization test.
Llama has approximately 3.21B parameters, Qwen 3.09B, and DeepSeek 1.5B;
the smaller DeepSeek size and its Qwen-derived architecture confound a pure
family comparison.
