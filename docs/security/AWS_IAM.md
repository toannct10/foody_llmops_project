# AWS IAM boundary

The application policy in `docs/cloud/AWS_IAM_POLICY.md` grants `ListBucket` on one bucket with `foody/*` prefix condition and `GetObject`/`PutObject` on `foody/raw/*` and `foody/manifests/*`. It grants no delete, IAM administration, bucket configuration or cross-bucket resource. The application identity can use an instance/task role or short-lived AWS SDK credentials.

The Snowflake storage integration uses a **different** AWS role: prefix-limited `ListBucket` and `GetObject` on RAW only. After Snowflake creates its integration, use `DESC INTEGRATION` to retrieve its actual IAM user ARN and external ID; set those in that role's trust policy and set `STORAGE_ALLOWED_LOCATIONS` to the same RAW prefix. Do not copy application write privileges into the Snowflake role. S3 bucket public access block and versioning are prerequisites, not implemented by this repository.

Static policy scope is tested offline. AWS policy simulation and actual S3 allow/deny probes remain live-cloud acceptance items.
