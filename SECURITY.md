# Security

## Model

- The Cloud Run service holds **no Akeyless keys**. It authenticates with its service account's Google ID token, and the Gateway keeps the target credentials.
- Tool and client responses contain secret **paths, metadata and results only**, never credential values.
- **Anyone who can invoke the service acts with its Akeyless role.** Deploy with `--no-allow-unauthenticated`, prefer `--ingress internal`, grant `roles/run.invoker` only to the agents and users that need it, and use one service plus one narrow Akeyless role per trust boundary.
- The invoker email added to `original_user` comes from the ID token Cloud Run IAM already verified. It is audit metadata, not an access-control input.
- TLS verification to the Gateway is always on. Use `AKEYLESS_CA_BUNDLE` for private CAs; never disable verification.
- The container runs as a non-root user.

## Operational guidance

- Do not log tokens, cloud IDs or tool payloads/results; they may contain sensitive data.
- Require human approval in the agent for any write, delete or other mutating `query-db` / `service-execute` call.
- Prefer `AKEYLESS_ACCESS_TYPE=gcp` in production. `access_key` is for local development only; if you must use it on Cloud Run, store the key in Secret Manager, not in plain env vars.

## Reporting a vulnerability

Please report security issues privately to security@akeyless.io rather than opening a public issue.
