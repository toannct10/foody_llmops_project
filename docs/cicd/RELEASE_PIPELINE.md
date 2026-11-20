# Release pipeline

`release.yml` supports `vMAJOR.MINOR.PATCH` tags and manual dispatch with an explicit version. It checks the version format, runs the tracked-file secret scan, validates base and DevOps Compose configuration, builds the application with `Dockerfile.rag`, and publishes to GHCR when the repository's `GITHUB_TOKEN` has `packages: write`. Tags include the version and `sha-<short commit>`; a stable tag push can also update `latest`. The release summary names the source commit and published tags.

The image is artifact-free: it does not contain GGUF weights, local Foody/Sales datasets, Chroma/BM25 indexes, SQLite telemetry, or cloud credentials. It is not a self-contained teammate package. No remote production deployment, AWS/Snowflake execution, or database migration is claimed by the release workflow.

Run `ci.yml` on the candidate commit before creating a release tag. Manual dispatch can publish from its selected ref; verify that ref and version are intentional. GHCR permissions or repository settings may block publication, and such a failure must remain visible rather than being reported as a deployment success.
