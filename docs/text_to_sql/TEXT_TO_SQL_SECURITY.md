# Text-to-SQL security policy

1. Parse PostgreSQL SQL with pinned `sqlglot`; require exactly one `SELECT` AST,
   optionally with read-only CTEs. Comments and internal/multiple semicolons are
   rejected; one terminal semicolon is removed before AST validation.
2. Reject DML, DDL, COPY, transactions, commands, lateral/subqueries, unions,
   OR/NOT expressions and wildcard selections. The function allowlist is
   SUM, COUNT, AVG, MIN, MAX, ROUND, COALESCE, NULLIF, DATE_TRUNC, EXTRACT,
   ABS, GREATEST and LEAST. A join must be on equal `restaurant_id` columns.
3. Reject unapproved or schema-qualified tables, unknown columns, unsupported
   functions, incorrect parameter sets, missing restaurant scope for ordinary
   questions and excessive/missing `LIMIT`. Maximum result is 100 rows.
4. Compare the chosen `restaurant_id` parameter with the UI-selected ID. Check
   explicit requested months against bound dates or date literals attached to
   `period_start` predicates. Reject gross sales
   when the user requests revenue; revenue means Delivered-only sales.
5. Open a separate PostgreSQL connection, begin a read-only transaction, set a
   5-second statement timeout and fetch no more than 101 rows. Errors are
   converted to non-secret categories. No rejected SQL reaches the executor.
   Single-month scalar results are compared with the existing parameterized
   monthly mart query; a mismatch triggers deterministic fallback.
6. One controlled regeneration is allowed for a validation rejection. On further
   failure, or when Qwen is unavailable, the existing deterministic planner runs.
7. Prometheus uses bounded policy categories and no question, SQL, restaurant ID
   or other unbounded label. The UI reveals generated SQL only in Technical
   details. Model output is never treated as an instruction to change policy.

The deployed database currently has an application user with write privileges
for ingestion. The Text-to-SQL executor adds a read-only transaction but a
dedicated database read-only role would provide a second privilege boundary.
That role is recommended before exposing Text-to-SQL beyond the local demo.
