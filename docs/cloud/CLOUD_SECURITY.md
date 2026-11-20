# Cloud security and failure boundaries

- Credentials come from the AWS SDK chain and Snowflake environment variables
  or a private key file. The public `.env.example` contains no values.
- The optional cloud Compose overlay reads a private `.env.cloud`, ignored by
  Git. Do not put production secrets in task arguments, XCom, source files or
  tracked reports. Cloud CLI prints only exception categories on failure.
- S3 IAM is limited to one bucket/prefix. The Snowflake stage uses a storage
  integration, not embedded AWS keys. The analytics role cannot ingest.
- A missing/altered S3 manifest or object blocks load. COPY aborts on CSV
  parsing errors. The staged row count, IDs and date range must reconcile with
  the locally accepted source before RAW insert.
- RAW insertion and the batch audit occur inside a transaction. Concurrent
  independent writers are **not** supported; keep one cloud DAG active and
  avoid manual simultaneous CLI loads. A separate distributed lock would be
  needed before multi-writer production use.
- Hash-addressed paths and conditional manifest registration prevent routine
  duplicate uploads. Do not grant `DeleteObject` or broad bucket permissions.
- Enforce Snowflake warehouse resource monitors and AWS budgets before a
  recurring cloud schedule. This DAG is paused/manual in this phase.
