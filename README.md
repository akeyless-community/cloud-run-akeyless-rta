# Akeyless RTA for Google Cloud Run

Let AI agents on Google Cloud query databases and act on cloud services **without ever holding credentials**. This package runs Akeyless **Agentic Runtime Authority** (RTA, also called ARA) on Cloud Run:

- The Cloud Run service signs in to Akeyless with its **service account** (GCP auth method). No Akeyless keys in env vars or images.
- Agents call `query-db` or `service-execute`; your **Akeyless Gateway** runs the query or action with credentials it keeps to itself and returns only results.
- Callers are gated by **Cloud Run IAM** (`roles/run.invoker`).

Two ways to use it:

| Mode | When |
|------|------|
| **MCP server on Cloud Run** | Any MCP client (ADK `MCPToolset`, Gemini, Claude, Cursor) |
| **Embedded client library** | Your agent already runs on Cloud Run and calls Python directly |

## Quick start

New to this? The [user guide](docs/USER_GUIDE.md) walks through setup, deploy, connecting an agent and the audit log end to end.

1. Set up the Gateway, auth method and role: [docs/AKEYLESS_SETUP.md](docs/AKEYLESS_SETUP.md)
2. Deploy: [docs/CLOUD_RUN_DEPLOY.md](docs/CLOUD_RUN_DEPLOY.md)

### Embedded

```bash
pip install akeyless-cloudrun-rta
```

```python
from akeyless_cloudrun_rta import AkeylessRtaClient

client = AkeylessRtaClient()  # AKEYLESS_GATEWAY_URL, AKEYLESS_ACCESS_ID from env; access type gcp
for secret in client.list_secrets():
    print(secret.name, secret.target_type)

result = client.query_db("SELECT count(*) FROM orders", secret_name="/prod/orders-db")
print(result.results)
```

### MCP server (local run)

```bash
pip install 'akeyless-cloudrun-rta[mcp]'
PORT=8080 akeyless-cloudrun-rta-mcp   # serves http://localhost:8080/mcp
```

## Tools

| Tool | Purpose |
|------|---------|
| `list-secrets` | RTA-enabled secrets: names and types only (hidden when `AKEYLESS_DEFAULT_SECRET_NAME` is set) |
| `query-db` | SQL / NoSQL query on a database secret |
| `service-execute` | Cloud, Kubernetes, GitHub, custom MCP action, or a remote command on SSH / Windows / LDAP items |
| `list-sub-tools` | Optional discovery for service secrets and remote items |

Tool names, descriptions and arguments match the Akeyless Go MCP server (`akeyless mcp-runtime-authority`) and the [Bedrock AgentCore package](https://github.com/akeyless-community/bedrock-agentcore-akeyless-rta).

## Examples

- [examples/adk-agent/embedded_agent](examples/adk-agent/embedded_agent/agent.py): ADK agent with the client as function tools
- [examples/adk-agent/mcp_agent](examples/adk-agent/mcp_agent/agent.py): ADK agent calling the Cloud Run MCP server

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,mcp]'
pytest
```

Releases are automated from tags; see [docs/RELEASING.md](docs/RELEASING.md).

## License

Apache-2.0
