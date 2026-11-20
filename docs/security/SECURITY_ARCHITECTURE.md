# Security architecture

Local: Streamlit → unsafe-question pre-check → pinned Qwen candidate → Pydantic JSON contract → SQL AST allowlists → optional `foody_ai_readonly` connection → read-only PostgreSQL transaction with timeout/row cap → deterministic result verification. A missing `FOODY_AI_DATABASE_URL` preserves the accepted local demo login; the SQL validator and read-only transaction remain active.

Cloud: application/Airflow IAM writes immutable Sales/Review RAW objects under one S3 prefix. Snowflake's storage integration assumes a distinct read-only AWS role. `FOODY_INGEST_ROLE` loads RAW, `FOODY_TRANSFORM_ROLE` reads RAW and builds STAGING/MART, and `FOODY_AI_READONLY_ROLE` reads only explicitly approved MART relations. Cloud DAG quality gates block publication on failure.

SQLite LLMOps security events contain timestamp, component, status, category and optional request/run/model ID. They contain no SQL, question text, exception string, password or key. Application API errors return a fixed service-unavailable message. This is single-machine demo audit storage, not a tamper-proof centralized log.
