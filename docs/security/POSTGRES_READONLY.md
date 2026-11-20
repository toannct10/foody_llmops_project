# PostgreSQL AI read-only role

`sql/postgres/readonly.sql` is an **optional** post-migration setup script. It creates login `foody_ai_readonly`, schema `ai_sales`, and four owner-backed views matching the Text-to-SQL allowlist. It grants CONNECT, schema USAGE and SELECT on those views only. No fact/base table or write privilege is granted. Its default search path is `ai_sales`, so existing unqualified validated SELECTs resolve to the approved views.

After migrations 001–004, apply with the local admin/owner:

```powershell
Get-Content sql/postgres/readonly.sql -Raw | docker compose -f docker-compose.yml -f docker-compose.devops.yml exec -T postgres psql -v ON_ERROR_STOP=1 -U foody -d foody
docker compose -f docker-compose.yml -f docker-compose.devops.yml exec postgres psql -U foody -d foody
```

In interactive `psql`, set a private password with `\password foody_ai_readonly`, then exit. Set `FOODY_AI_DATABASE_URL` privately for the Streamlit process, using `postgres` as host inside Compose or `127.0.0.1:5433` on the host. Never put the real DSN in Git or a test report. Restart only Streamlit to pick it up.

Verify under the role: `SELECT count(*) FROM restaurant_monthly_sales` must succeed; `INSERT`, `UPDATE`, `DELETE` and `CREATE` against `ai_sales` must fail with permission errors. Test both an approved view and an unapproved `public.fact_order` read. A plain local demo without the optional DSN continues to use the prior connection and transaction-level read-only guard. Enable the dedicated role before describing the demo as least-privilege database execution.
