# S3 data lake layout

The configured root is `s3://$FOODY_S3_BUCKET/$FOODY_S3_PREFIX/` (default
prefix `foody`). Objects are content-addressed:

```text
foody/raw/sales/version=sales_orders_v1/sha256=<64-hex>/order_cleaning.csv
foody/raw/reviews/version=review_2025_2026_v1/sha256=<64-hex>/data_2025_2026.csv
foody/manifests/sales/<64-hex>.json
foody/manifests/reviews/<64-hex>.json
```

The per-source manifest records name, original filename, key, byte size,
source row count, SHA256, UTC upload time, source version, date range and the
joint Sales/Review batch ID. `HEAD` and the manifest are checked before upload.
A registered hash with matching object size/metadata returns
`SKIPPED_DUPLICATE`; conflicting metadata fails. The manifest write uses an
S3 conditional `IfNoneMatch=*` request for concurrent registration safety.
For prefix-scoped IAM, a missing `HEAD` may return 403; the client checks the
exact key with an authorized prefix-scoped `ListObjectsV2` before treating it
as absent. Other access errors still fail closed.
Objects use S3-managed encryption (`AES256`). Enable bucket versioning and
block public access in the AWS account. S3 ETag is **not** treated as SHA256.
