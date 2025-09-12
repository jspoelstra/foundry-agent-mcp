# foundry-agent-mcp

Demo Azure AI MCP (Model Context Protocol) agent project that demonstrates interacting with an MCP server via Azure AI Agents SDK using `McpTool` capabilities.

## Overview
This project shows how to:
- Configure and register an MCP server as a tool with an Azure AI Agent
- Create an agent, thread, message, and run lifecycle
- Handle tool approval workflows (manual approval pattern)
- Iterate run status and inspect run steps & tool call metadata
- Dynamically manage allowed tools at runtime

The core logic lives in `demo.py`.

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
# (Optionally export manually if not using a loader like python-dotenv)

# Ensure you're authenticated (one option):
az login

python demo.py
```

## Environment Variables
The script relies on the following (see `.env.example`):
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

## How It Works
1. Instantiate `AIProjectClient` with `DefaultAzureCredential`.
2. Create an `McpTool` representing the MCP server & dynamically adjust allowed tools.
3. Create an agent with tool definitions.
4. Create a thread & initial user message.
5. Create a run and poll status until completion (handling `requires_action` for tool approval).
6. Enumerate run steps & print structured tool call metadata.
7. List conversation messages.
8. Demonstrate dynamic tool removal.
9. Clean up the agent.

## Tool Approval Flow
When `run.status == "requires_action"` and the action payload contains `RequiredMcpToolCall`, the script approves each call by constructing `ToolApproval` objects and submitting them.

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
