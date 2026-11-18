# Akeyless setup for RTA on Cloud Run

Do this before deploying the MCP server.

## 1. Gateway with RTA (ARA)

You need a **customer or self-hosted Akeyless Gateway** with Agentic Runtime Authority enabled, configured per the [product docs](https://docs.akeyless.io/docs/agentic-runtime-authority). On Google Cloud, run it on **GKE or a GCE VM** inside the VPC that can reach your targets (Cloud SQL, GKE, private hosts). The Cloud Run service reaches it over Direct VPC egress.

```bash
export AKEYLESS_GATEWAY_URL=https://10.0.0.5:8000
```

Do **not** use `https://api.akeyless.io`: the public SaaS API does not host the RTA execute endpoints, and this library rejects that host.

If the Gateway uses a privately signed certificate, mount the CA as a file (for example from Secret Manager as a volume) and set `AKEYLESS_CA_BUNDLE=/path/ca.pem`. TLS verification is never disabled.

## 2. Service account

Create a dedicated service account for the Cloud Run service. One service account (and one Akeyless role) per trust boundary.

```bash
gcloud iam service-accounts create akeyless-rta --display-name "Akeyless RTA (Cloud Run)"
```

The service account exists before deploy, so you can bind it in Akeyless right away. There is no deploy-then-bind step like on AgentCore.

## 3. GCP auth method

```bash
akeyless auth-method create gcp \
  --name cloud-run-rta \
  --type iam \
  --audience akeyless.io \
  --bound-service-accounts akeyless-rta@PROJECT_ID.iam.gserviceaccount.com
```

Use the returned access ID (`p-...`) as `AKEYLESS_ACCESS_ID`. If you change `--audience`, set the same value in `AKEYLESS_GCP_AUDIENCE`.

## 4. RBAC: RTA allow access

Associate the auth method with a role that grants:

- List / Read on the secret paths you will expose
- An **Agentic Runtime Authority** rule with **Allow Access** (`ara_allow_access`) on those paths

Enable RTA on each dynamic or rotated secret in the Console (or equivalent API). Keep the role narrow: every caller of the Cloud Run service acts with it.

## 5. Verify locally

Impersonate the service account so the ID token matches the bound identity:

```bash
gcloud auth application-default login --impersonate-service-account \
  akeyless-rta@PROJECT_ID.iam.gserviceaccount.com

export AKEYLESS_GATEWAY_URL=https://gw.internal.example.com:8000
export AKEYLESS_ACCESS_ID=p-xxxxx

python -c "from akeyless_cloudrun_rta import AkeylessRtaClient; print(AkeylessRtaClient().list_secrets())"
```

`access_key` (`AKEYLESS_ACCESS_TYPE=access_key`) also works for local testing. You should see secret **names and target types** only, never passwords or keys.
