# foundry-agent-mcp

Demo Azure AI MCP (Model Context Protocol) agent project that demonstrates interacting with an MCP server via Azure AI Agents SDK using `McpTool` capabilities.

## Overview
This project is a refactor of code example documented [here](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol-samples?pivots=python) and shows how to:
- Configure and register an MCP server as a tool with an Azure AI Agent
- Create an agent, thread, message, and run lifecycle
- Handle tool approval workflows (manual approval pattern)
- Iterate run status and inspect run steps & tool call metadata
- Dynamically manage allowed tools at runtime

The single-file demo has been split into two clearer scripts:

1. `create-agent.py` – One‑time (or occasional) creation of an Azure AI Agent pre‑configured with the MCP tool. Persists the agent ID in a local mapping file (`.agents.json`).
2. `run-agent.py` – Starts an interactive chat session using an existing agent (looked up by name in `.agents.json`). Handles message submission, run polling, and MCP tool approval.

This separation lets you reuse the same agent across sessions without re‑creating it every time.

## Requirements
- Python 3.11+
- Azure subscription & access to Azure AI services supporting Agents
- An endpoint & model deployment (e.g., Azure OpenAI compatible) 
- Properly configured credentials for `DefaultAzureCredential` (e.g. `az login`, managed identity, or environment variables)

## Quick Start
```bash
# Clone (if not already)
# git clone <repo-url>
cd foundry-agent-mcp

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]

# Copy environment template and edit values
cp .env.example .env
# (Or export vars manually; python-dotenv is used opportunistically by the scripts.)

# Authenticate (one option)
az login

# 1. Create (or update) an agent once. Name becomes a key in .agents.json
python create-agent.py \
	--name my-mcp-agent \
	--model "$MODEL_DEPLOYMENT_NAME" \
	--mcp-url "${MCP_SERVER_URL:-https://gitmcp.io/Azure/azure-rest-api-specs}" \
	--mcp-label "${MCP_SERVER_LABEL:-github}" 

# 2. Start an interactive session with that agent
python run-agent.py --name my-mcp-agent

# Type messages; use :quit (or Ctrl-D) to exit.
```

### Reusing / Listing Agents
The file `.agents.json` stores a simple JSON object mapping agent names to their IDs:
```json
{
	"my-mcp-agent": "agt_123..."
}
```
You can create multiple differently configured agents (e.g., pointing to different MCP servers) by running `create-agent.py` with new `--name` values.

### Deleting / Cleaning Up Agents
Agents are not automatically deleted. If you want to remove one:
1. Delete (or edit) its entry from `.agents.json` locally.
2. Optionally call the Azure AI Agents API / SDK `delete_agent(agent_id)` (not yet scripted here) if you wish to remove it server-side.

## Environment Variables
Both scripts rely on the following (see `.env.example`):
| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` | Yes | Azure AI project endpoint URL (e.g., https://YOUR-RESOURCE.openai.azure.com) |
| `MODEL_DEPLOYMENT_NAME` | Yes | Name of the deployed model to use for the agent |
| `MCP_SERVER_URL` | No (default provided) | URL of the MCP server endpoint to register |
| `MCP_SERVER_LABEL` | No (default provided) | Short label identifying the MCP server |

### Loading `.env`
You can export manually or use a utility such as `dotenv` in your shell/profile. Example manual export:
```bash
export PROJECT_ENDPOINT="https://my-ai-resource.openai.azure.com"
export MODEL_DEPLOYMENT_NAME="gpt-4o"
```

## How It Works (Split Flow)
Creation phase (`create-agent.py`):
1. Loads env vars and resolves model & endpoint.
2. Builds an `McpTool` definition using `server_label` + `server_url`.
3. Creates the agent (idempotent at the user level—creating again with the same name just overwrites local mapping, not the remote agent).
4. Writes the agent ID to `.agents.json` for reuse.

Interaction phase (`run-agent.py`):
1. Looks up the agent ID by name in `.agents.json` and validates existence via `get_agent`.
2. Creates a new thread per session.
3. For each user input: creates a message, then a run referencing the persistent agent.
4. Polls run status. On `REQUIRES_ACTION`, auto-approves any `RequiredMcpToolCall` entries (simple policy; you could prompt the user instead).
5. After completion, fetches latest assistant response and enumerates tool steps for transparency.
6. Leaves the agent intact for future sessions.

## Tool Approval Flow
When a run transitions to `REQUIRES_ACTION` with `SubmitToolApprovalAction`, any `RequiredMcpToolCall` items are auto‑approved in the current implementation. For finer control you can modify `run-agent.py` to:
- Prompt the user before approving
- Deny selectively (`approve=False`)
- Log the tool arguments for auditing

## Development
### Linting & Type Checking
```bash
ruff check .
mypy .
```

### Formatting (if desired)
```bash
ruff format .
```

### Tests (none yet)
Add tests under `tests/` using `pytest` naming conventions (`test_*.py`). Example command:
```bash
pytest
```

### Security Scan
```bash
bandit -r .
```

### Coverage
```bash
coverage run -m pytest
coverage report -m
```

## Extending
Suggested enhancements:
- Extract agent orchestration into a reusable module (e.g., `agent_runner.py`).
- Add retry/backoff logic around transient API calls.
- Introduce structured logging (JSON) for observability.
- Add test doubles for Azure clients (e.g., using `pytest` fixtures + monkeypatch).
- Implement graceful cancellation (signal handling) for long runs.

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Authentication error | Credential chain empty | Run `az login` or set env vars (CLIENT_ID, TENANT_ID, CLIENT_SECRET) |
| 404 / model not found | Wrong `MODEL_DEPLOYMENT_NAME` | Check deployed model name in Azure portal |
| Run stuck in `queued` | Service latency or invalid tool config | Verify MCP server URL, inspect logs |
| `requires_action` loops | Not submitting approvals | Ensure approval block executes & tool calls present |

## License
MIT License – see `LICENSE` if added; default text defined in `pyproject.toml`.

## Contributing
Follow internal guidelines in `.github/instructions/python.instructions.md`. Open PRs with clear rationale and keep changes small & reviewable.

---
Generated README; adjust model names / endpoint values to match your Azure environment.
