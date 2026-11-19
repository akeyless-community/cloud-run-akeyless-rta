#!/usr/bin/env bash
# Deploy the Akeyless RTA MCP server to Cloud Run with a dedicated service
# account, IAM-only ingress and, for a private Gateway, VPC egress.
#
# Required env:
#   PROJECT_ID, REGION
#   AKEYLESS_GATEWAY_URL   Gateway URL with ARA enabled, e.g. https://10.0.0.5:8000
#   AKEYLESS_ACCESS_ID     Akeyless GCP auth method access ID (p-...)
#   INVOKER_MEMBERS        space-separated IAM members allowed to call the service,
#                          e.g. "serviceAccount:my-agent@proj.iam.gserviceaccount.com user:me@example.com"
# Optional env:
#   NETWORK, SUBNET        set both for Direct VPC egress to a private Gateway;
#                          leave both unset when the Gateway has a public address
#   SERVICE_NAME (akeyless-rta), SA_NAME (akeyless-rta), INGRESS (internal),
#   AKEYLESS_GCP_AUDIENCE (akeyless.io), AKEYLESS_DEFAULT_SECRET_NAME, REPOSITORY (akeyless)
set -euo pipefail

: "${PROJECT_ID:?PROJECT_ID is required}"
: "${REGION:?REGION is required}"
if { [[ -n "${NETWORK:-}" ]] && [[ -z "${SUBNET:-}" ]]; } || { [[ -z "${NETWORK:-}" ]] && [[ -n "${SUBNET:-}" ]]; }; then
  echo "Set both NETWORK and SUBNET for VPC egress, or neither for a public Gateway" >&2
  exit 1
fi
: "${AKEYLESS_GATEWAY_URL:?AKEYLESS_GATEWAY_URL is required}"
: "${AKEYLESS_ACCESS_ID:?AKEYLESS_ACCESS_ID is required}"
: "${INVOKER_MEMBERS:?INVOKER_MEMBERS is required}"

SERVICE_NAME="${SERVICE_NAME:-akeyless-rta}"
SA_NAME="${SA_NAME:-akeyless-rta}"
INGRESS="${INGRESS:-internal}"
REPOSITORY="${REPOSITORY:-akeyless}"
AKEYLESS_GCP_AUDIENCE="${AKEYLESS_GCP_AUDIENCE:-akeyless.io}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:$(date +%Y%m%d%H%M%S)"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" \
    --project "$PROJECT_ID" \
    --display-name "Akeyless RTA (Cloud Run)"
fi

if ! gcloud artifacts repositories describe "$REPOSITORY" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format docker \
    --location "$REGION" \
    --project "$PROJECT_ID"
fi

gcloud builds submit "$ROOT_DIR" --tag "$IMAGE" --project "$PROJECT_ID"

ENV_VARS="AKEYLESS_GATEWAY_URL=${AKEYLESS_GATEWAY_URL},AKEYLESS_ACCESS_ID=${AKEYLESS_ACCESS_ID},AKEYLESS_ACCESS_TYPE=gcp,AKEYLESS_GCP_AUDIENCE=${AKEYLESS_GCP_AUDIENCE}"
if [[ -n "${AKEYLESS_DEFAULT_SECRET_NAME:-}" ]]; then
  ENV_VARS="${ENV_VARS},AKEYLESS_DEFAULT_SECRET_NAME=${AKEYLESS_DEFAULT_SECRET_NAME}"
fi

VPC_FLAGS=()
if [[ -n "${NETWORK:-}" ]]; then
  VPC_FLAGS=(--network "$NETWORK" --subnet "$SUBNET" --vpc-egress private-ranges-only)
fi

gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE" \
  --service-account "$SA_EMAIL" \
  --no-allow-unauthenticated \
  --ingress "$INGRESS" \
  ${VPC_FLAGS[@]+"${VPC_FLAGS[@]}"} \
  --timeout 300 \
  --set-env-vars "$ENV_VARS"

for member in $INVOKER_MEMBERS; do
  gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --member "$member" \
    --role roles/run.invoker
done

echo "Deployed ${SERVICE_NAME}. Bind ${SA_EMAIL} in your Akeyless GCP auth method if you have not already."
