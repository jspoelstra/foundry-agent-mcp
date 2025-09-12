"""Create an Azure AI Agent with an MCP tool and persist its ID for later runs.

Minimal extraction from original demo. Stores mapping of agent names to IDs in `.agents.json`.

Usage:
    python create-agent.py --name my-mcp-agent \
        --model $MODEL_DEPLOYMENT_NAME \
        [--mcp-url https://gitmcp.io/Azure/azure-rest-api-specs] \
        [--mcp-label github]

Environment variables required:
    PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME (if not passed via --model)

Supports loading a local .env file via python-dotenv if installed.

Outputs:
    Prints created agent ID and updates .agents.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import McpTool

AGENT_STORE_FILE = Path(".agents.json")


def load_store() -> Dict[str, str]:
    if AGENT_STORE_FILE.exists():
        try:
            return json.loads(AGENT_STORE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_store(store: Dict[str, str]) -> None:
    AGENT_STORE_FILE.write_text(json.dumps(store, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an Azure AI agent with MCP tool")
    parser.add_argument("--name", required=True, help="Human-friendly agent name (unique key)")
    parser.add_argument("--model", help="Model deployment name (overrides env MODEL_DEPLOYMENT_NAME)")
    parser.add_argument("--mcp-url", dest="mcp_url", default=os.environ.get("MCP_SERVER_URL", "https://gitmcp.io/Azure/azure-rest-api-specs"), help="MCP server URL")
    parser.add_argument("--mcp-label", dest="mcp_label", default=os.environ.get("MCP_SERVER_LABEL", "github"), help="MCP server label")
    return parser.parse_args()


def main() -> None:
    # Load environment variables from .env if python-dotenv is available
    load_dotenv(override=False)

    args = parse_args()

    model = args.model or os.environ.get("MODEL_DEPLOYMENT_NAME")
    if not model:
        raise SystemExit("Model deployment name must be provided via --model or MODEL_DEPLOYMENT_NAME env var")

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        raise SystemExit("PROJECT_ENDPOINT env var is required")

    project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

    with project_client:
        agents_client = project_client.agents

        # Build MCP tool
        mcp_tool = McpTool(
            server_label=args.mcp_label,
            server_url=args.mcp_url,
        )

        agent = agents_client.create_agent(
            model=model,
            name=args.name,
            instructions=(
                "You are a helpful agent that can use MCP tools to assist users. "
                "Use the available MCP tools to answer questions and perform tasks."
            ),
            tools=mcp_tool.definitions,
        )

    store = load_store()
    store[args.name] = agent.id
    save_store(store)
    print(f"Created agent '{args.name}' with ID: {agent.id}")
    print(f"Stored mapping in {AGENT_STORE_FILE}")


if __name__ == "__main__":  # pragma: no cover
    main()
