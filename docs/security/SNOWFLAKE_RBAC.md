# Snowflake RBAC

`sql/snowflake/bootstrap.sql` creates three scoped roles. The ingest role has warehouse/database/RAW usage, stage/file-format usage, RAW SELECT/INSERT and RAW CREATE TABLE solely for temporary COPY landing tables. The transform role has RAW SELECT plus STAGING/MART CREATE TABLE/VIEW. Neither role has account-admin grants. Assign each role only to the Snowflake user that runs that step.

The AI role has warehouse/database/MART usage only. After a successful dbt run, an authorized grant owner applies `sql/snowflake/grant_ai_readonly.sql`: SELECT on `DIM_RESTAURANT` and five named analytical views. It excludes RAW, STAGING and the order/review fact tables. The grant script uses the default `FOODY` database; adapt identifiers to a nondefault database before use.

Existing installations that received the older broad future MART grants must first review and apply `sql/snowflake/revoke_legacy_ai_grants.sql`, then apply the explicit allowlist. Revocation is a separate upgrade step so fresh bootstrap remains idempotent. Live role grants and denied write/read probes remain pending Snowflake credentials.
