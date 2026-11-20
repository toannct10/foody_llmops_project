# AWS least-privilege policy

Replace `YOUR_BUCKET` and `foody` with the configured bucket and prefix.
Attach the first policy to the application/Airflow identity. It cannot read
other buckets, delete objects or administer IAM. A separate Snowflake storage
integration role should receive only `s3:ListBucket` on this prefix and
`s3:GetObject` on `foody/raw/*`; it does **not** need application write access.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListFoodyPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::YOUR_BUCKET",
      "Condition": {"StringLike": {"s3:prefix": ["foody/*"]}}
    },
    {
      "Sid": "ReadWriteFoodyObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET/foody/raw/*",
        "arn:aws:s3:::YOUR_BUCKET/foody/manifests/*"
      ]
    }
  ]
}
```

The Snowflake integration trust policy requires the Snowflake-generated IAM
user ARN and external ID from `DESC INTEGRATION`; obtain those after an admin
creates the integration. Scope the integration's allowed location to
`s3://YOUR_BUCKET/foody/raw/`. Do not create AWS users or paste long-lived keys
into Compose, SQL, Git or Airflow task parameters.
